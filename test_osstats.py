import pytest
import redis
from unittest.mock import Mock, patch, MagicMock
import configparser
import asyncio
from osstats import (
    get_value,
    native_str,
    parse_response,
    create_workbook,
    get_command_by_args,
    get_redis_client,
    process_node,
    process_database,
    main,
)


class TestGetValue:
    def test_get_value_int(self):
        assert get_value("123") == 123

    def test_get_value_float(self):
        assert get_value("123.45") == 123.45

    def test_get_value_string(self):
        assert get_value("hello") == "hello"

    def test_get_value_dict(self):
        result = get_value("key1=val1,key2=val2")
        assert result == {"key1": "val1", "key2": "val2"}

    def test_get_value_nested_dict(self):
        result = get_value("key1=123,key2=45.6")
        assert result == {"key1": 123, "key2": 45.6}


class TestNativeStr:
    def test_native_str_string(self):
        assert native_str("hello") == "hello"

    def test_native_str_bytes(self):
        assert native_str(b"hello") == "hello"

    def test_native_str_bytes_with_encoding_error(self):
        # Test with invalid UTF-8 bytes
        result = native_str(b"\xff\xfe")
        assert isinstance(result, str)


class TestParseResponse:
    def test_parse_response_basic(self):
        response = "key1:value1\nkey2:123\nkey3:45.6"
        result = parse_response(response)
        assert result == {"key1": "value1", "key2": 123, "key3": 45.6}

    def test_parse_response_with_comments(self):
        response = "# This is a comment\nkey1:value1\n# Another comment\nkey2:123"
        result = parse_response(response)
        assert result == {"key1": "value1", "key2": 123}

    def test_parse_response_cmdstat_host(self):
        response = "cmdstat_host:calls=1,usec=100"
        result = parse_response(response)
        assert "cmdstat_host" in result

    def test_parse_response_raw_lines(self):
        response = "key1:value1\ninvalid_line_without_colon"
        result = parse_response(response)
        assert result["key1"] == "value1"
        assert "__raw__" in result
        assert "invalid_line_without_colon" in result["__raw__"]


class TestCreateWorkbook:
    def test_create_workbook(self):
        wb = create_workbook()
        assert wb is not None
        assert wb.active.title == "ClusterData"


class TestGetCommandByArgs:
    def test_get_command_by_args(self):
        cmds1 = {"cmdstat_get": {"calls": 100}, "cmdstat_set": {"calls": 50}}
        cmds2 = {"cmdstat_get": {"calls": 150}, "cmdstat_set": {"calls": 80}}

        result = get_command_by_args(cmds1, cmds2, "get", "set")
        assert result == 80  # (150-100) + (80-50)

    def test_get_command_by_args_missing_command(self):
        cmds1 = {"cmdstat_get": {"calls": 100}}
        cmds2 = {"cmdstat_get": {"calls": 150}}

        result = get_command_by_args(cmds1, cmds2, "get", "missing")
        assert result == 50  # Only get command exists


class TestGetRedisClient:
    @patch("osstats.redis.Redis")
    def test_get_redis_client_basic(self, mock_redis):
        client = get_redis_client("localhost", 6379)
        mock_redis.assert_called_once()
        args = mock_redis.call_args[1]
        assert args["host"] == "localhost"
        assert args["port"] == 6379
        assert args["ssl"] is False

    @patch("osstats.redis.Redis")
    def test_get_redis_client_with_auth(self, mock_redis):
        client = get_redis_client("localhost", 6379, password="pass", username="user")
        args = mock_redis.call_args[1]
        assert args["password"] == "pass"
        assert args["username"] == "user"

    @patch("osstats.redis.Redis")
    def test_get_redis_client_with_tls(self, mock_redis):
        client = get_redis_client("localhost", 6379, tls=True, ca_cert="/path/ca.crt")
        args = mock_redis.call_args[1]
        assert args["ssl"] is True
        assert args["ssl_cert_reqs"] == "required"
        assert args["ssl_ca_certs"] == "/path/ca.crt"


class TestProcessNode:
    @pytest.mark.asyncio
    @patch("osstats.get_redis_client")
    @patch("osstats.parse_response")
    @patch("osstats.sleep")
    async def test_process_node(self, mock_sleep, mock_parse, mock_get_client):
        # Mock configuration
        config = Mock()

        def mock_get(key, default=None, fallback=None):
            values = {
                "host": "localhost",
                "port": "6379",
                "password": None,
                "username": None,
                "ca_cert": None,
                "client_cert": None,
                "client_key": None,
            }
            return values.get(key, fallback or default)

        config.get.side_effect = mock_get
        config.getboolean.return_value = False

        # Mock Redis client
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock Redis responses - return parsed dictionaries directly
        mock_info_dict = {
            "redis_version": "6.2.0",
            "os": "Linux",
            "total_system_memory": 8589934592,
            "used_memory_peak": 1048576,
            "connected_clients": 10,
            "cluster_enabled": 0,
            "total_commands_processed": 1000,
            "db0": {"keys": 100, "expires": 0},
        }
        mock_info_dict2 = mock_info_dict.copy()
        mock_info_dict2["total_commands_processed"] = 1200

        mock_client.execute_command.side_effect = [
            "cmdstat_get:calls=100,usec=1000",  # First commandstats
            mock_info_dict,  # First info - return dict directly
            "cmdstat_get:calls=150,usec=1500",  # Second commandstats
            mock_info_dict2,  # Second info - return dict directly
        ]

        # Mock parse_response to return proper dictionaries
        mock_parse.side_effect = [
            {"cmdstat_get": {"calls": 100, "usec": 1000}},
            {"cmdstat_get": {"calls": 150, "usec": 1500}},
        ]

        result = await process_node("test-section", config, "localhost:6379", True, 1)

        assert result is not None
        assert result["Source"] == "OSS"
        assert result["ClusterId"] == "test-section"
        assert result["NodeRole"] == "Master"


if __name__ == "__main__":
    pytest.main([__file__])
