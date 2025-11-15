# DragonSync Refactoring Plan

## Executive Summary
Transform DragonSync from a monolithic script into a modular, testable, and maintainable architecture following SOLID principles and clean architecture patterns.

---

## Target Architecture Overview

```
DragonSync/
├── dragonsync/
│   ├── __init__.py
│   ├── core/                    # Domain logic (no external dependencies)
│   │   ├── __init__.py
│   │   ├── models.py           # Data models (Drone, Aircraft, SystemStatus)
│   │   ├── cot.py              # CoT message generation logic
│   │   └── tracking.py         # Drone/aircraft tracking & state management
│   │
│   ├── inputs/                  # Data ingestion adapters
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base classes
│   │   ├── zmq_drone.py        # ZMQ 4224 drone telemetry
│   │   ├── zmq_status.py       # ZMQ 4225 system status
│   │   └── adsb.py             # ADS-B/UAT HTTP API client
│   │
│   ├── outputs/                 # Data export adapters
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base classes
│   │   ├── tak_multicast.py    # Multicast CoT sender
│   │   ├── tak_server.py       # TAK server TCP/UDP/TLS client
│   │   ├── mqtt.py             # MQTT publisher
│   │   └── lattice.py          # Lattice API client
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py           # Config file parsing
│   │   ├── validator.py        # Config validation
│   │   └── models.py           # Config dataclasses
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main event loop & coordination
│   │   ├── rate_limiter.py     # Rate limiting logic
│   │   └── timeout_manager.py  # Inactivity timeout handling
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Structured logging setup
│       ├── converters.py       # Type conversions & utilities
│       └── gps.py              # GPS handling (GPSD + static fallback)
│
├── tests/
│   ├── __init__.py
│   ├── integration/            # End-to-end tests
│   │   ├── test_zmq_to_tak.py
│   │   ├── test_adsb_to_cot.py
│   │   └── test_mqtt_ha.py
│   │
│   ├── unit/                   # Module-specific tests
│   │   ├── core/
│   │   │   ├── test_models.py
│   │   │   ├── test_cot.py
│   │   │   └── test_tracking.py
│   │   ├── inputs/
│   │   ├── outputs/
│   │   └── services/
│   │
│   └── fixtures/               # Test data & mocks
│       ├── sample_zmq_messages.json
│       ├── sample_adsb_response.json
│       └── mock_config.ini
│
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   └── development.md
│
├── main.py                     # Entry point
├── config.ini.example
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pyproject.toml
└── README.md
```

---

## Phase 1: Foundation & Core Models (Week 1)

### Task 1.1: Project Structure Setup
**Priority: CRITICAL**
**Estimated Time: 2 hours**

- [ ] Create new branch `refactor/phase-1-foundation`
- [ ] Set up Python package structure with proper `__init__.py` files
- [ ] Create `pyproject.toml` for modern Python packaging
- [ ] Split `requirements.txt` into base and dev dependencies
- [ ] Add `.gitignore` for Python projects
- [ ] Set up basic logging configuration

**Success Criteria:**
- Package can be imported: `import dragonsync`
- All dependencies install cleanly
- Logging outputs structured JSON logs

---

### Task 1.2: Define Core Data Models
**Priority: CRITICAL**
**Estimated Time: 4 hours**

Create `dragonsync/core/models.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class DroneType(Enum):
    REMOTE_ID_BLE = "remote_id_ble"
    REMOTE_ID_WIFI = "remote_id_wifi"
    DJI = "dji"
    UNKNOWN = "unknown"

class AircraftCategory(Enum):
    """ADS-B aircraft categories"""
    NO_INFO = 0
    LIGHT = 1
    SMALL = 2
    LARGE = 3
    # ... etc

@dataclass
class Position:
    """Geographic position with metadata"""
    latitude: float
    longitude: float
    altitude: float  # meters MSL
    timestamp: datetime
    accuracy_horizontal: Optional[float] = None  # CE
    accuracy_vertical: Optional[float] = None    # LE
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        ...

@dataclass
class Drone:
    """Drone detection data model"""
    id: str  # Unique identifier (MAC, serial, etc)
    drone_type: DroneType
    position: Position
    speed: Optional[float] = None  # m/s
    heading: Optional[float] = None  # degrees
    vertical_speed: Optional[float] = None  # m/s
    rssi: Optional[float] = None
    frequency: Optional[float] = None  # MHz
    
    # Optional pilot/home positions
    pilot_position: Optional[Position] = None
    home_position: Optional[Position] = None
    
    # Metadata
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs) -> None:
        """Update drone data and refresh timestamp"""
        self.last_updated = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

@dataclass
class Aircraft:
    """ADS-B aircraft data model"""
    hex: str  # ICAO hex code
    position: Position
    callsign: Optional[str] = None
    squawk: Optional[str] = None
    speed: Optional[float] = None  # m/s
    heading: Optional[float] = None
    vertical_rate: Optional[float] = None
    category: Optional[AircraftCategory] = None
    on_ground: bool = False
    registration: Optional[str] = None
    
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SystemStatus:
    """WarDragon system status"""
    serial_number: str
    position: Position
    temperature: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
```

**Tests to Write:**
- [ ] `tests/unit/core/test_models.py`
  - Test Position validation and serialization
  - Test Drone update logic and timestamp handling
  - Test all dataclass constructors with edge cases

**Success Criteria:**
- All models have clean, type-annotated interfaces
- Models are immutable where appropriate
- Serialization to dict works correctly
- Tests achieve >90% coverage

---

### Task 1.3: Configuration Management
**Priority: CRITICAL**
**Estimated Time: 6 hours**

Create `dragonsync/config/`:

```python
# models.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ZMQConfig:
    host: str = "127.0.0.1"
    drone_port: int = 4224
    status_port: int = 4225

@dataclass
class TAKServerConfig:
    enabled: bool = False
    host: str = ""
    port: int = 8089
    protocol: str = "tcp"  # tcp, udp
    tls_p12_path: Optional[str] = None
    tls_password: Optional[str] = None
    skip_verify: bool = True

@dataclass
class TAKMulticastConfig:
    enabled: bool = True
    address: str = "239.2.3.1"
    port: int = 6969
    interface: str = "0.0.0.0"
    ttl: int = 1

@dataclass
class MQTTConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    tls: bool = False
    # ... HA-specific settings

@dataclass
class LatticeConfig:
    enabled: bool = False
    token: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    drone_rate: float = 1.0
    wd_rate: float = 0.2

@dataclass
class ADSBConfig:
    enabled: bool = False
    json_url: str = "http://127.0.0.1:8080/?all_with_pos"
    min_altitude: int = 0
    max_altitude: int = 0
    poll_interval: float = 1.0

@dataclass
class RuntimeConfig:
    rate_limit: float = 3.0
    max_drones: int = 30
    inactivity_timeout: float = 60.0

@dataclass
class DragonSyncConfig:
    """Master configuration"""
    zmq: ZMQConfig
    tak_server: TAKServerConfig
    tak_multicast: TAKMulticastConfig
    mqtt: MQTTConfig
    lattice: LatticeConfig
    adsb: ADSBConfig
    runtime: RuntimeConfig

# loader.py
class ConfigLoader:
    @staticmethod
    def from_ini(path: str) -> DragonSyncConfig:
        """Load config from INI file"""
        ...
    
    @staticmethod
    def from_env() -> DragonSyncConfig:
        """Load config from environment variables (12-factor)"""
        ...

# validator.py
class ConfigValidator:
    @staticmethod
    def validate(config: DragonSyncConfig) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Checks:
        - At least one output is enabled
        - TLS files exist if TLS enabled
        - Port numbers are valid
        - Rate limits are positive
        - URLs are well-formed
        """
        ...
```

**Tests to Write:**
- [ ] `tests/unit/config/test_loader.py`
  - Load from sample INI
  - Load with missing sections (use defaults)
  - Load with invalid values (should raise)
- [ ] `tests/unit/config/test_validator.py`
  - Validate valid config
  - Catch common misconfigurations

**Success Criteria:**
- Config loading is type-safe
- Validation catches common errors at startup
- Default values match current behavior
- Environment variable overrides work

---

## Phase 2: Core Domain Logic (Week 2)

### Task 2.1: CoT Message Generator
**Priority: HIGH**
**Estimated Time: 8 hours**

Create `dragonsync/core/cot.py`:

```python
from typing import Optional
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from .models import Drone, Aircraft, SystemStatus, Position

class CoTGenerator:
    """
    Generates Cursor on Target (CoT) XML messages.
    
    Pure function - no side effects, fully testable.
    """
    
    @staticmethod
    def from_drone(drone: Drone, observer_pos: Position) -> str:
        """
        Generate CoT message for a drone detection.
        
        Returns XML string in CoT format.
        """
        ...
    
    @staticmethod
    def from_aircraft(aircraft: Aircraft, observer_pos: Position) -> str:
        """Generate CoT message for ADS-B aircraft"""
        ...
    
    @staticmethod
    def from_system(status: SystemStatus) -> str:
        """Generate CoT message for system status"""
        ...
    
    @staticmethod
    def _build_event(
        uid: str,
        event_type: str,
        how: str,
        position: Position,
        stale_minutes: int = 5
    ) -> ET.Element:
        """Build base CoT event element"""
        ...
    
    @staticmethod
    def _add_detail(
        event: ET.Element,
        callsign: str,
        remarks: str,
        **kwargs
    ) -> None:
        """Add detail section to CoT event"""
        ...
```

**Tests to Write:**
- [ ] `tests/unit/core/test_cot.py`
  - Generate drone CoT and validate XML structure
  - Generate aircraft CoT with all ADS-B fields
  - Test CE/LE calculation from NACp/NACv
  - Test coordinate precision
  - Test stale time calculation
  - Validate against CoT schema if available

**Success Criteria:**
- Generated CoT validates against spec
- All edge cases handled (missing fields, etc)
- No external dependencies (pure function)
- Messages match current format exactly

---

### Task 2.2: Tracking & State Management
**Priority: HIGH**
**Estimated Time: 8 hours**

Create `dragonsync/core/tracking.py`:

```python
from typing import Dict, Optional, Callable, List
from datetime import datetime, timedelta
from .models import Drone, Aircraft

class TrackingManager:
    """
    Manages state for all tracked objects (drones, aircraft).
    
    Responsibilities:
    - Deduplicate updates
    - Track first/last seen timestamps
    - Detect inactive tracks
    - Rate limiting per object
    """
    
    def __init__(
        self,
        max_tracks: int = 30,
        inactivity_timeout: float = 60.0,
        rate_limit: float = 3.0,
        on_timeout_callback: Optional[Callable[[str], None]] = None
    ):
        self._drones: Dict[str, Drone] = {}
        self._aircraft: Dict[str, Aircraft] = {}
        self._last_sent: Dict[str, datetime] = {}
        self._max_tracks = max_tracks
        self._inactivity_timeout = timedelta(seconds=inactivity_timeout)
        self._rate_limit = timedelta(seconds=rate_limit)
        self._on_timeout = on_timeout_callback
    
    def update_drone(self, drone: Drone) -> Optional[Drone]:
        """
        Update or add drone to tracking.
        
        Returns:
            Drone object if it should be sent (rate limit passed)
            None if rate limited
        """
        now = datetime.utcnow()
        
        # Update existing or add new
        if drone.id in self._drones:
            self._drones[drone.id].update(**drone.__dict__)
        else:
            if len(self._drones) >= self._max_tracks:
                # Evict oldest inactive drone
                self._evict_oldest()
            self._drones[drone.id] = drone
        
        # Check rate limit
        last_sent = self._last_sent.get(drone.id)
        if last_sent and (now - last_sent) < self._rate_limit:
            return None
        
        self._last_sent[drone.id] = now
        return self._drones[drone.id]
    
    def update_aircraft(self, aircraft: Aircraft) -> Optional[Aircraft]:
        """Similar logic for aircraft"""
        ...
    
    def check_timeouts(self) -> List[str]:
        """
        Check for inactive tracks and mark them as timed out.
        
        Returns:
            List of IDs that timed out
        """
        now = datetime.utcnow()
        timed_out = []
        
        for drone_id, drone in list(self._drones.items()):
            if (now - drone.last_updated) > self._inactivity_timeout:
                timed_out.append(drone_id)
                if self._on_timeout:
                    self._on_timeout(drone_id)
                del self._drones[drone_id]
                self._last_sent.pop(drone_id, None)
        
        # Same for aircraft
        ...
        
        return timed_out
    
    def get_all_active(self) -> Dict[str, Drone]:
        """Return all currently tracked drones"""
        return self._drones.copy()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest drone by last_updated"""
        if not self._drones:
            return
        oldest_id = min(
            self._drones.keys(),
            key=lambda k: self._drones[k].last_updated
        )
        del self._drones[oldest_id]
```

**Tests to Write:**
- [ ] `tests/unit/core/test_tracking.py`
  - Test rate limiting (should block rapid updates)
  - Test timeout detection
  - Test max tracks eviction
  - Test callback invocation on timeout
  - Test drone update merging

**Success Criteria:**
- Rate limiting works correctly
- Timeouts trigger callbacks
- Memory bounded by max_tracks
- No race conditions (if we add threading later)

---

## Phase 3: Input Adapters (Week 3)

### Task 3.1: Abstract Input Interface
**Priority: HIGH**
**Estimated Time: 2 hours**

Create `dragonsync/inputs/base.py`:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Callable
from dragonsync.core.models import Drone, Aircraft, SystemStatus

class InputAdapter(ABC):
    """Abstract base class for all input sources"""
    
    def __init__(self, config: Any, on_error: Optional[Callable] = None):
        self.config = config
        self._on_error = on_error
        self._running = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to input source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection"""
        pass
    
    @abstractmethod
    async def stream(self) -> AsyncIterator[Union[Drone, Aircraft, SystemStatus]]:
        """
        Yield objects as they arrive.
        
        This is an async generator that continuously yields
        parsed domain objects.
        """
        pass
    
    async def start(self) -> None:
        """Start the adapter"""
        await self.connect()
        self._running = True
    
    async def stop(self) -> None:
        """Stop the adapter"""
        self._running = False
        await self.disconnect()
```

---

### Task 3.2: ZMQ Drone Input
**Priority: HIGH**
**Estimated Time: 6 hours**

Create `dragonsync/inputs/zmq_drone.py`:

```python
import zmq
import zmq.asyncio
import json
from typing import AsyncIterator
from .base import InputAdapter
from dragonsync.core.models import Drone, DroneType, Position

class ZMQDroneInput(InputAdapter):
    """
    Listens to ZMQ port 4224 for drone telemetry.
    
    Expects JSON messages with Remote ID or DJI data.
    """
    
    def __init__(self, config: ZMQConfig, on_error=None):
        super().__init__(config, on_error)
        self._context = None
        self._socket = None
    
    async def connect(self) -> None:
        self._context = zmq.asyncio.Context()
        self._socket = self._context.socket(zmq.SUB)
        url = f"tcp://{self.config.host}:{self.config.drone_port}"
        self._socket.connect(url)
        self._socket.setsockopt_string(zmq.SUBSCRIBE, "")
    
    async def disconnect(self) -> None:
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()
    
    async def stream(self) -> AsyncIterator[Drone]:
        while self._running:
            try:
                message = await self._socket.recv_string()
                drone = self._parse_message(message)
                if drone:
                    yield drone
            except Exception as e:
                if self._on_error:
                    self._on_error(e)
                # Consider: exponential backoff on errors
    
    def _parse_message(self, message: str) -> Optional[Drone]:
        """
        Parse raw ZMQ JSON into Drone object.
        
        Handles both Remote ID and DJI formats.
        """
        try:
            data = json.loads(message)
            
            # Determine drone type from message structure
            if "BasicID" in data:
                return self._parse_remote_id(data)
            elif "dji" in data.get("type", "").lower():
                return self._parse_dji(data)
            
            return None
        except json.JSONDecodeError:
            return None
    
    def _parse_remote_id(self, data: dict) -> Drone:
        """Parse Remote ID format"""
        ...
    
    def _parse_dji(self, data: dict) -> Drone:
        """Parse DJI format"""
        ...
```

**Tests to Write:**
- [ ] `tests/unit/inputs/test_zmq_drone.py`
  - Mock ZMQ socket and test message parsing
  - Test Remote ID parsing
  - Test DJI parsing
  - Test error handling
  - Test connection lifecycle

---

### Task 3.3: ZMQ Status Input
**Priority: MEDIUM**
**Estimated Time: 4 hours**

Create `dragonsync/inputs/zmq_status.py` - similar pattern to drone input.

---

### Task 3.4: ADS-B HTTP Input
**Priority: MEDIUM**
**Estimated Time: 6 hours**

Create `dragonsync/inputs/adsb.py`:

```python
import aiohttp
from typing import AsyncIterator, List
from .base import InputAdapter
from dragonsync.core.models import Aircraft, Position

class ADSBInput(InputAdapter):
    """
    Polls readsb HTTP API for aircraft data.
    
    Converts ADS-B JSON to Aircraft objects.
    """
    
    def __init__(self, config: ADSBConfig, on_error=None):
        super().__init__(config, on_error)
        self._session = None
    
    async def connect(self) -> None:
        self._session = aiohttp.ClientSession()
    
    async def disconnect(self) -> None:
        if self._session:
            await self._session.close()
    
    async def stream(self) -> AsyncIterator[Aircraft]:
        while self._running:
            try:
                aircraft_list = await self._fetch_aircraft()
                for aircraft in aircraft_list:
                    yield aircraft
                
                await asyncio.sleep(self.config.poll_interval)
            except Exception as e:
                if self._on_error:
                    self._on_error(e)
    
    async def _fetch_aircraft(self) -> List[Aircraft]:
        """Fetch and parse aircraft from readsb API"""
        async with self._session.get(self.config.json_url) as resp:
            data = await resp.json()
            return [
                self._parse_aircraft(ac)
                for ac in data.get("aircraft", [])
                if self._should_include(ac)
            ]
    
    def _should_include(self, aircraft_data: dict) -> bool:
        """Apply altitude filters"""
        alt = aircraft_data.get("alt_baro") or aircraft_data.get("alt_geom")
        if alt is None:
            return True
        
        if self.config.min_altitude and alt < self.config.min_altitude:
            return False
        if self.config.max_altitude and alt > self.config.max_altitude:
            return False
        
        return True
    
    def _parse_aircraft(self, data: dict) -> Aircraft:
        """Convert readsb JSON to Aircraft model"""
        ...
```

**Tests to Write:**
- [ ] `tests/unit/inputs/test_adsb.py`
  - Mock HTTP responses
  - Test altitude filtering
  - Test NACp/NACv to CE/LE conversion
  - Test missing field handling

---

## Phase 4: Output Adapters (Week 4)

### Task 4.1: Abstract Output Interface
**Priority: HIGH**
**Estimated Time: 2 hours**

Create `dragonsync/outputs/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional, Callable
from dragonsync.core.models import Drone, Aircraft, SystemStatus

class OutputAdapter(ABC):
    """Abstract base class for all output destinations"""
    
    def __init__(self, config: Any, on_error: Optional[Callable] = None):
        self.config = config
        self._on_error = on_error
        self._running = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to output destination"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection"""
        pass
    
    @abstractmethod
    async def send_drone(self, drone: Drone, cot_xml: str) -> None:
        """Send drone data"""
        pass
    
    @abstractmethod
    async def send_aircraft(self, aircraft: Aircraft, cot_xml: str) -> None:
        """Send aircraft data"""
        pass
    
    async def send_timeout(self, object_id: str) -> None:
        """
        Optional: handle timeout notifications.
        
        For MQTT/HA, this marks entities as unavailable.
        For TAK, this might send a deletion message.
        """
        pass
```

---

### Task 4.2: TAK Multicast Output
**Priority: HIGH**
**Estimated Time: 4 hours**

Create `dragonsync/outputs/tak_multicast.py`:

```python
import socket
import struct
from .base import OutputAdapter

class TAKMulticastOutput(OutputAdapter):
    """
    Sends CoT messages via UDP multicast.
    
    Simple broadcast for ATAK on same network.
    """
    
    def __init__(self, config: TAKMulticastConfig, on_error=None):
        super().__init__(config, on_error)
        self._socket = None
    
    async def connect(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 
                               struct.pack('b', self.config.ttl))
    
    async def disconnect(self) -> None:
        if self._socket:
            self._socket.close()
    
    async def send_drone(self, drone: Drone, cot_xml: str) -> None:
        await self._send(cot_xml)
    
    async def send_aircraft(self, aircraft: Aircraft, cot_xml: str) -> None:
        await self._send(cot_xml)
    
    async def _send(self, cot_xml: str) -> None:
        try:
            self._socket.sendto(
                cot_xml.encode('utf-8'),
                (self.config.address, self.config.port)
            )
        except Exception as e:
            if self._on_error:
                self._on_error(e)
```

---

### Task 4.3: TAK Server Output
**Priority: HIGH**
**Estimated Time: 8 hours**

Create `dragonsync/outputs/tak_server.py` - handles TCP/UDP/TLS connections.

**Key Challenges:**
- TLS certificate handling (.p12 files)
- Connection pooling & reconnection
- Protocol detection (TCP vs UDP)

---

### Task 4.4: MQTT/Home Assistant Output
**Priority: MEDIUM**
**Estimated Time: 10 hours**

Create `dragonsync/outputs/mqtt.py`:

```python
import asyncio_mqtt as aiomqtt
import json
from typing import Dict, Any
from .base import OutputAdapter

class MQTTOutput(OutputAdapter):
    """
    Publishes drone data to MQTT with Home Assistant discovery.
    
    Creates device trackers and sensors per drone.
    """
    
    def __init__(self, config: MQTTConfig, on_error=None):
        super().__init__(config, on_error)
        self._client = None
        self._discovered = set()  # Track which drones have been discovered
    
    async def connect(self) -> None:
        self._client = aiomqtt.Client(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            # TLS config if enabled
        )
        await self._client.__aenter__()
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
    
    async def send_drone(self, drone: Drone, cot_xml: str) -> None:
        # Send HA discovery if first time seeing this drone
        if drone.id not in self._discovered:
            await self._publish_discovery(drone)
            self._discovered.add(drone.id)
        
        # Publish state
        await self._publish_state(drone)
    
    async def send_timeout(self, drone_id: str) -> None:
        """Mark drone as unavailable in HA"""
        topic = f"{self.config.per_drone_base}/{drone_id}/state"
        payload = json.dumps({"available": False})
        await self._client.publish(topic, payload, retain=True)
    
    async def _publish_discovery(self, drone: Drone) -> None:
        """
        Publish Home Assistant MQTT discovery messages.
        
        Creates:
        - device_tracker for drone position
        - device_tracker for pilot position (if available)
        - device_tracker for home position (if available)
        - sensors for altitude, speed, RSSI, etc.
        """
        ...
    
    async def _publish_state(self, drone: Drone) -> None:
        """Publish current drone state"""
        ...
    
    def _build_discovery_config(self, drone: Drone, entity_type: str) -> Dict[str, Any]:
        """Build HA discovery config payload"""
        ...
```

**Tests to Write:**
- [ ] `tests/unit/outputs/test_mqtt.py`
  - Test discovery message format
  - Test state updates
  - Test timeout handling
  - Validate JSON payloads match HA expectations

---

### Task 4.5: Lattice Output
**Priority: LOW**
**Estimated Time: 6 hours**

Create `dragonsync/outputs/lattice.py` - REST API client for Anduril Lattice.

---

## Phase 5: Service Layer & Orchestration (Week 5)

### Task 5.1: Rate Limiter Service
**Priority: MEDIUM**
**Estimated Time: 3 hours**

Already incorporated into TrackingManager, but could be extracted for reuse.

---

### Task 5.2: Main Orchestrator
**Priority: CRITICAL**
**Estimated Time: 10 hours**

Create `dragonsync/services/orchestrator.py`:

```python
import asyncio
from typing import List
from dragonsync.config.models import DragonSyncConfig
from dragonsync.core.tracking import TrackingManager
from dragonsync.core.cot import CoTGenerator
from dragonsync.inputs.base import InputAdapter
from dragonsync.outputs.base import OutputAdapter

class DragonSyncOrchestrator:
    """
    Main application orchestrator.
    
    Responsibilities:
    - Coordinate all input and output adapters
    - Manage tracking state
    - Generate CoT messages
    - Route data to appropriate outputs
    - Handle graceful shutdown
    """
    
    def __init__(
        self,
        config: DragonSyncConfig,
        inputs: List[InputAdapter],
        outputs: List[OutputAdapter]
    ):
        self.config = config
        self._inputs = inputs
        self._outputs = outputs
        self._tracker = TrackingManager(
            max_tracks=config.runtime.max_drones,
            inactivity_timeout=config.runtime.inactivity_timeout,
            rate_limit=config.runtime.rate_limit,
            on_timeout_callback=self._handle_timeout
        )
        self._cot_gen = CoTGenerator()
        self._tasks = []
        self._running = False
    
    async def start(self) -> None:
        """Start all adapters and begin processing"""
        self._running = True
        
        # Connect all adapters
        for input_adapter in self._inputs:
            await input_adapter.start()
        
        for output_adapter in self._outputs:
            await output_adapter.connect()
        
        # Start processing tasks
        for input_adapter in self._inputs:
            task = asyncio.create_task(self._process_input(input_adapter))
            self._tasks.append(task)
        
        # Start timeout checker
        timeout_task = asyncio.create_task(self._check_timeouts())
        self._tasks.append(timeout_task)
    
    async def stop(self) -> None:
        """Graceful shutdown"""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Disconnect adapters
        for input_adapter in self._inputs:
            await input_adapter.stop()
        
        for output_adapter in self._outputs:
            await output_adapter.disconnect()
    
    async def _process_input(self, adapter: InputAdapter) -> None:
        """Process objects from an input adapter"""
        async for obj in adapter.stream():
            if isinstance(obj, Drone):
                await self._handle_drone(obj)
            elif isinstance(obj, Aircraft):
                await self._handle_aircraft(obj)
            elif isinstance(obj, SystemStatus):
                await self._handle_system_status(obj)
    
    async def _handle_drone(self, drone: Drone) -> None:
        """Process drone update"""
        # Check rate limit via tracker
        tracked_drone = self._tracker.update_drone(drone)
        if not tracked_drone:
            return  # Rate limited
        
        # Generate CoT
        system_pos = self._get_system_position()
        cot_xml = self._cot_gen.from_drone(tracked_drone, system_pos)
        
        # Send to all outputs
        await self._broadcast(tracked_drone, None, cot_xml)
    
    async def _handle_aircraft(self, aircraft: Aircraft) -> None:
        """Process aircraft update"""
        tracked = self._tracker.update_aircraft(aircraft)
        if not tracked:
            return
        
        system_pos = self._get_system_position()
        cot_xml = self._cot_gen.from_aircraft(tracked, system_pos)
        
        await self._broadcast(None, tracked, cot_xml)
    
    async def _broadcast(
        self,
        drone: Optional[Drone],
        aircraft: Optional[Aircraft],
        cot_xml: str
    ) -> None:
        """Send data to all configured outputs"""
        tasks = []
        for output in self._outputs:
            if drone:
                task = output.send_drone(drone, cot_xml)
            else:
                task = output.send_aircraft(aircraft, cot_xml)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_timeouts(self) -> None:
        """Periodically check for inactive tracks"""
        while self._running:
            await asyncio.sleep(10)  # Check every 10 seconds
            timed_out = self._tracker.check_timeouts()
            
            # Notify outputs
            for obj_id in timed_out:
                for output in self._outputs:
                    await output.send_timeout(obj_id)
    
    async def _handle_timeout(self, obj_id: str) -> None:
        """Callback from tracker when object times out"""
        # Already handled in _check_timeouts
        pass
    
    def _get_system_position(self) -> Position:
        """Get current system position from status or static GPS"""
        # TODO: implement GPS handling
        ...
```

**Tests to Write:**
- [ ] `tests/integration/test_orchestrator.py`
  - Mock inputs/outputs and verify flow
  - Test timeout handling
  - Test graceful shutdown
  - Test rate limiting integration

---

### Task 5.3: Main Entry Point
**Priority: CRITICAL**
**Estimated Time: 4 hours**

Create `main.py`:

```python
import asyncio
import signal
import sys
from pathlib import Path
from dragonsync.config import ConfigLoader, ConfigValidator
from dragonsync.services.orchestrator import DragonSyncOrchestrator
from dragonsync.inputs import ZMQDroneInput, ZMQStatusInput, ADSBInput
from dragonsync.outputs import (
    TAKMulticastOutput,
    TAKServerOutput,
    MQTTOutput,
    LatticeOutput
)
from dragonsync.utils.logging import setup_logging

async def main():
    # Parse args
    import argparse
    parser = argparse.ArgumentParser(description="DragonSync - Drone tracking gateway")
    parser.add_argument("-c", "--config", default="config.ini", help="Config file path")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load and validate config
    config = ConfigLoader.from_ini(args.config)
    errors = ConfigValidator.validate(config)
    if errors:
        for error in errors:
            print(f"Config error: {error}", file=sys.stderr)
        sys.exit(1)
    
    # Build inputs
    inputs = []
    inputs.append(ZMQDroneInput(config.zmq))
    inputs.append(ZMQStatusInput(config.zmq))
    if config.adsb.enabled:
        inputs.append(ADSBInput(config.adsb))
    
    # Build outputs
    outputs = []
    if config.tak_multicast.enabled:
        outputs.append(TAKMulticastOutput(config.tak_multicast))
    if config.tak_server.enabled:
        outputs.append(TAKServerOutput(config.tak_server))
    if config.mqtt.enabled:
        outputs.append(MQTTOutput(config.mqtt))
    if config.lattice.enabled:
        outputs.append(LatticeOutput(config.lattice))
    
    if not outputs:
        print("ERROR: No outputs enabled in config!", file=sys.stderr)
        sys.exit(1)
    
    # Create orchestrator
    orchestrator = DragonSyncOrchestrator(config, inputs, outputs)
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown():
        print("Shutting down gracefully...")
        asyncio.create_task(orchestrator.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    
    # Run
    try:
        await orchestrator.start()
        # Keep running until shutdown
        while orchestrator._running:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 6: Integration Tests & Documentation (Week 6)

### Task 6.1: End-to-End Integration Tests
**Priority: HIGH**
**Estimated Time: 12 hours**

```python
# tests/integration/test_zmq_to_tak.py
async def test_zmq_drone_to_multicast():
    """
    Test full flow: ZMQ input -> Tracking -> CoT -> Multicast output
    """
    # Setup mock ZMQ server
    # Setup multicast listener
    # Inject test drone data
    # Verify CoT received on multicast
    # Verify rate limiting
    # Verify timeout handling

# tests/integration/test_adsb_to_cot.py
async def test_adsb_to_tak():
    """Test ADS-B HTTP -> Aircraft -> CoT flow"""
    ...

# tests/integration/test_mqtt_ha.py
async def test_mqtt_homeassistant_discovery():
    """
    Test MQTT output with HA discovery.
    
    Verify:
    - Discovery messages sent
    - State updates published
    - Timeout marks unavailable
    """
    ...
```

---

### Task 6.2: Documentation
**Priority: MEDIUM**
**Estimated Time: 8 hours**

- [ ] `docs/architecture.md` - Architecture diagrams, design decisions
- [ ] `docs/configuration.md` - Complete config reference
- [ ] `docs/development.md` - Setup, testing, contributing guide
- [ ] Update main `README.md` with new structure
- [ ] Add docstrings to all public APIs
- [ ] Generate API docs with Sphinx

---

### Task 6.3: Migration Guide
**Priority: MEDIUM**
**Estimated Time: 4 hours**

Create `MIGRATION.md`:

- How to migrate from old monolithic script
- Config file changes (if any)
- New features/capabilities
- Breaking changes (if any)

---

## Phase 7: Polish & Deployment (Week 7)

### Task 7.1: Performance Optimization
**Priority: LOW**
**Estimated Time: 6 hours**

- [ ] Profile with `cProfile` and `py-spy`
- [ ] Optimize hot paths (CoT generation, JSON parsing)
- [ ] Add connection pooling where beneficial
- [ ] Benchmark against old version

---

### Task 7.2: Error Handling & Resilience
**Priority: MEDIUM**
**Estimated Time: 6 hours**

- [ ] Add retry logic with exponential backoff
- [ ] Implement circuit breakers for failing outputs
- [ ] Add health check endpoints
- [ ] Improve error messages and logging

---

### Task 7.3: Deployment Tooling
**Priority: MEDIUM**
**Estimated Time: 4 hours**

- [ ] Update systemd service file
- [ ] Create Docker container (optional)
- [ ] Add installation script
- [ ] Create release process (tagging, changelog)

---

## Success Metrics

### Code Quality
- [ ] >80% unit test coverage
- [ ] >60% integration test coverage
- [ ] All tests passing in CI
- [ ] No critical issues in static analysis (mypy, ruff)

### Functional
- [ ] Feature parity with original script
- [ ] All integration paths tested (ZMQ, ADS-B, TAK, MQTT, Lattice)
- [ ] Handles edge cases gracefully
- [ ] Performance within 10% of original

### Maintainability
- [ ] Clear module boundaries
- [ ] Each module <500 lines
- [ ] No circular dependencies
- [ ] Comprehensive documentation

---

## Risk Mitigation

### Risk: Breaking Changes
**Mitigation:**
- Keep feature branch until fully tested
- Run old and new versions in parallel during testing
- Create comprehensive integration tests first

### Risk: Performance Regression
**Mitigation:**
- Benchmark early and often
- Profile before optimization
- Use same libraries where possible

### Risk: Scope Creep
**Mitigation:**
- Stick to refactoring; no new features
- Use strict phase gates
- Track tasks in GitHub issues

---

## Daily Workflow

1. **Morning:** Review task list, pick highest priority
2. **Development:** TDD approach - write test first, then implementation
3. **Afternoon:** Code review (if team) or self-review checklist
4. **End of day:** Commit progress, update task list

## Tools & Libraries

**Core:**
- `asyncio` - Async/await for I/O
- `zmq.asyncio` - Async ZMQ
- `aiohttp` - Async HTTP client
- `asyncio-mqtt` - Async MQTT client

**Testing:**
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

**Code Quality:**
- `mypy` - Type checking
- `ruff` - Fast linting/formatting
- `black` - Code formatting (if not using ruff)
- `isort` - Import sorting

**Documentation:**
- `sphinx` - API documentation
- `mkdocs` - User documentation (alternative to Sphinx)

---

## Next Steps

1. Review this plan and adjust priorities based on your constraints
2. Set up project tracking (GitHub Projects, Jira, etc.)
3. Create feature branch: `refactor/phase-1-foundation`
4. Start with Phase 1, Task 1.1

Would you like me to:
1. Generate starter code for any specific module?
2. Create test fixtures/mocks?
3. Set up the project structure with all directories?
4. Dive deeper into any particular phase?
