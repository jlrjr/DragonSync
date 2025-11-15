"""
Unit tests for configuration loading and validation.
"""

import pytest
from pathlib import Path
from dragonsync.config.loader import ConfigLoader
from dragonsync.config.validator import ConfigValidator
from dragonsync.config.models import DragonSyncConfig


class TestConfigLoader:
    """Test configuration loading"""
    
    def test_load_mock_config(self):
        """Test loading the mock config.ini"""
        # Get path to mock config
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
        config_path = fixtures_dir / "mock_config.ini"
        
        config = ConfigLoader.from_ini(str(config_path))
        
        assert isinstance(config, DragonSyncConfig)
        
        # Check ZMQ settings
        assert config.zmq.host == "127.0.0.1"
        assert config.zmq.drone_port == 4224
        assert config.zmq.status_port == 4225
        
        # Check multicast is enabled
        assert config.tak_multicast.enabled is True
        assert config.tak_multicast.port == 6969
        
        # Check runtime settings
        assert config.runtime.rate_limit == 1.0
        assert config.runtime.max_drones == 10
        assert config.runtime.inactivity_timeout == 30.0
        
        # Check GPS settings
        assert config.gps.use_static is True
        assert config.gps.static_lat == 42.3601
    
    def test_load_nonexistent_file(self):
        """Test error handling for missing config file"""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.from_ini("/nonexistent/config.ini")
    
    def test_config_defaults(self):
        """Test that defaults are applied for missing sections"""
        # Create a minimal config file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[SETTINGS]\n")
            f.write("zmq_host = 192.168.1.100\n")
            config_path = f.name
        
        try:
            config = ConfigLoader.from_ini(config_path)
            
            # Custom value should be loaded
            assert config.zmq.host == "192.168.1.100"
            
            # Defaults should be used for missing values
            assert config.zmq.drone_port == 4224
            assert config.runtime.rate_limit == 3.0
        finally:
            Path(config_path).unlink()


class TestConfigValidator:
    """Test configuration validation"""
    
    def test_valid_config(self):
        """Test validation of valid config"""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
        config_path = fixtures_dir / "mock_config.ini"
        config = ConfigLoader.from_ini(str(config_path))
        
        errors = ConfigValidator.validate(config)
        
        assert len(errors) == 0
    
    def test_no_outputs_enabled(self):
        """Test error when no outputs are enabled"""
        config = DragonSyncConfig()
        config.tak_multicast.enabled = False
        config.tak_server.enabled = False
        config.mqtt.enabled = False
        config.lattice.enabled = False
        
        errors = ConfigValidator.validate(config)
        
        assert len(errors) > 0
        assert any("No outputs enabled" in err for err in errors)
    
    def test_invalid_port_numbers(self):
        """Test validation of port numbers"""
        config = DragonSyncConfig()
        config.zmq.drone_port = 99999  # Invalid port
        
        errors = ConfigValidator.validate(config)
        
        assert len(errors) > 0
        assert any("Invalid ZMQ drone port" in err for err in errors)
    
    def test_tak_server_validation(self):
        """Test TAK server specific validation"""
        config = DragonSyncConfig()
        config.tak_server.enabled = True
        config.tak_server.host = ""  # Empty host
        config.tak_server.protocol = "invalid"  # Invalid protocol
        
        errors = ConfigValidator.validate(config)
        
        assert len(errors) >= 2
        assert any("no host specified" in err for err in errors)
        assert any("Invalid TAK protocol" in err for err in errors)
    
    def test_adsb_altitude_validation(self):
        """Test ADS-B altitude filter validation"""
        config = DragonSyncConfig()
        config.adsb.enabled = True
        config.adsb.json_url = "http://test.com"
        config.adsb.min_altitude = 10000
        config.adsb.max_altitude = 5000  # Max less than min
        
        errors = ConfigValidator.validate(config)
        
        assert any("min_altitude" in err and "max_altitude" in err for err in errors)
    
    def test_gps_coordinate_validation(self):
        """Test static GPS coordinate validation"""
        config = DragonSyncConfig()
        config.tak_multicast.enabled = True  # Need at least one output
        config.gps.use_static = True
        config.gps.static_lat = 200.0  # Invalid
        config.gps.static_lon = -200.0  # Invalid
        
        errors = ConfigValidator.validate(config)
        
        assert len(errors) >= 2
        assert any("latitude" in err for err in errors)
        assert any("longitude" in err for err in errors)
