import {
  ApiDomain,
  ApiEndpoint,
  DetectionIngestPreset,
  DetectionIngestionResult,
  DetectionValidationResult,
  DispatchedResponse,
  SchemaDefinition,
} from '../types/developer';

export const API_DOMAINS: ApiDomain[] = [
  'Platform & Health',
  'Authentication & Session',
  'Sensor Ingestion',
  'Tracking & Fusion',
  'Intelligence & Defense',
  'Simulation & Scenarios',
  'Historical & Analytics',
  'Governance & RBAC',
];

export const API_CATALOG: ApiEndpoint[] = [
  // 1. Platform & Health
  {
    id: 'health_get',
    domain: 'Platform & Health',
    name: 'Database & System Health',
    method: 'GET',
    path: '/health',
    description: 'Public health probe executing SELECT 1 database connectivity verification.',
    responseDescription: 'Application status, version, and database connection state.',
  },
  {
    id: 'system_info_get',
    domain: 'Platform & Health',
    name: 'Runtime Specifications & Environment',
    method: 'GET',
    path: '/system/info',
    description: 'Protected system runtime specifications, Python engine details, and platform architecture.',
    requiredPermission: 'system.read',
    responseDescription: 'Application version, environment, debug status, and OS platform information.',
  },

  // 2. Authentication & Session
  {
    id: 'auth_login_post',
    domain: 'Authentication & Session',
    name: 'Operator Session Login',
    method: 'POST',
    path: '/auth/login',
    description: 'Authenticate operator credentials and establish an opaque HttpOnly session cookie.',
    requestBodySchema: 'LoginRequest',
    requestBodyTemplate: JSON.stringify({ username: 'operator', password: 'password123' }, null, 2),
    responseDescription: 'Authenticated user profile, assigned roles, and permission list.',
  },
  {
    id: 'auth_logout_post',
    domain: 'Authentication & Session',
    name: 'Operator Session Logout',
    method: 'POST',
    path: '/auth/logout',
    description: 'Terminate active operator session and revoke server-side session hash.',
    responseDescription: 'Logout confirmation status.',
  },
  {
    id: 'auth_me_get',
    domain: 'Authentication & Session',
    name: 'Current Session Profile',
    method: 'GET',
    path: '/me',
    description: 'Retrieve identity, account status, and authority permissions of active operator session.',
    responseDescription: 'Current user ID, username, roles, and granted permissions.',
  },

  // 3. Sensor Ingestion
  {
    id: 'sensors_list_get',
    domain: 'Sensor Ingestion',
    name: 'List Registered Sensors',
    method: 'GET',
    path: '/sensors',
    description: 'List registered sensor systems, modalities, coverage parameters, and operational status.',
    requiredPermission: 'sensors.read',
    queryParams: [
      { name: 'status', type: 'string', required: false, description: 'Filter by sensor status (ACTIVE, DEGRADED, OFFLINE)' },
      { name: 'source_type', type: 'string', required: false, description: 'Filter by modality (RADAR, RF, OPTICAL)' },
      { name: 'limit', type: 'number', required: false, description: 'Max items to return (1-100)', defaultValue: 50 },
      { name: 'offset', type: 'number', required: false, description: 'Item offset for pagination', defaultValue: 0 },
    ],
    responseDescription: 'List of registered sensors with coordinates, range, and FOV azimuth parameters.',
  },
  {
    id: 'sensor_detail_get',
    domain: 'Sensor Ingestion',
    name: 'Sensor Profile & Status',
    method: 'GET',
    path: '/sensors/{sensor_id}',
    description: 'Query detailed telemetry and spatial parameters for a single registered sensor.',
    requiredPermission: 'sensors.read',
    pathParams: [
      { name: 'sensor_id', type: 'string', required: true, description: 'Unique UUID of the target sensor' },
    ],
    responseDescription: 'Detailed sensor model with range, accuracy, position noise, and FOV span.',
  },
  {
    id: 'sensors_detection_post',
    domain: 'Sensor Ingestion',
    name: 'Ingest Sensor Observation',
    method: 'POST',
    path: '/sensors/{sensor_id}/detections',
    description: 'Submit a normalized observation detection to the ingestion pipeline for track correlation.',
    requiredPermission: 'sensors.configure',
    pathParams: [
      { name: 'sensor_id', type: 'string', required: true, description: 'Unique UUID of the target sensor' },
    ],
    requestBodySchema: 'RawDetection',
    requestBodyTemplate: JSON.stringify(
      {
        source_detection_id: 'det-radar-001',
        timestamp: new Date().toISOString(),
        latitude: 37.7749,
        longitude: -122.4194,
        altitude_m: 120.5,
        heading_deg: 45.0,
        speed_mps: 18.2,
        source_type: 'RADAR',
        confidence: 0.92,
        metadata: { snr_db: 18.5, rcs_dbsm: -5.0 },
      },
      null,
      2
    ),
    responseDescription: 'Detection ID, creation flag (created vs deduplicated), sensor ID, and timestamp.',
  },

  // 4. Tracking & Fusion
  {
    id: 'tracks_list_get',
    domain: 'Tracking & Fusion',
    name: 'Query Operational Tracks',
    method: 'GET',
    path: '/tracks',
    description: 'Retrieve active correlated tracks, kinematic estimates, classification, and confidence scoring.',
    requiredPermission: 'tracks.read',
    queryParams: [
      { name: 'state', type: 'string', required: false, description: 'Filter by track state (TENTATIVE, CONFIRMED, COASTING, CLOSED)' },
      { name: 'classification', type: 'string', required: false, description: 'Filter by classification (DRONE, BIRD, AIRCRAFT, UNKNOWN)' },
      { name: 'limit', type: 'number', required: false, description: 'Max items per page', defaultValue: 50 },
      { name: 'cursor', type: 'string', required: false, description: 'Cursor token for pagination' },
    ],
    responseDescription: 'Paginated list of operational tracks with source count, position, and kinematics.',
  },
  {
    id: 'track_detail_get',
    domain: 'Tracking & Fusion',
    name: 'Track Detail & Kinematics',
    method: 'GET',
    path: '/tracks/{track_id}',
    description: 'Query real-time fused state, velocity vector, classification consensus, and threat level for a track.',
    requiredPermission: 'tracks.read',
    pathParams: [
      { name: 'track_id', type: 'string', required: true, description: 'UUID of the operational track' },
    ],
    responseDescription: 'Full track entity with spatial coordinates, covariance, quality score, and associations.',
  },
  {
    id: 'track_history_get',
    domain: 'Tracking & Fusion',
    name: 'Track Kinematic History',
    method: 'GET',
    path: '/tracks/{track_id}/history',
    description: 'Retrieve append-only historical trajectory breadcrumbs and sensor association history for a track.',
    requiredPermission: 'tracks.read',
    pathParams: [
      { name: 'track_id', type: 'string', required: true, description: 'UUID of the operational track' },
    ],
    queryParams: [
      { name: 'limit', type: 'number', required: false, description: 'Max history entries', defaultValue: 100 },
      { name: 'cursor', type: 'string', required: false, description: 'Pagination cursor' },
    ],
    responseDescription: 'Sequential trajectory points with timestamps, coordinates, speed, and heading.',
  },

  // 5. Intelligence & Defense
  {
    id: 'alerts_list_get',
    domain: 'Intelligence & Defense',
    name: 'Operational Alerts Feed',
    method: 'GET',
    path: '/alerts',
    description: 'Query operational alerts triggered by geofence breaches, high-speed ingress, or anomalies.',
    requiredPermission: 'alerts.read',
    queryParams: [
      { name: 'status', type: 'string', required: false, description: 'Alert status (NEW, ACKNOWLEDGED, RESOLVED)' },
      { name: 'severity', type: 'string', required: false, description: 'Severity level (LOW, MEDIUM, HIGH, CRITICAL)' },
      { name: 'track_id', type: 'string', required: false, description: 'Associated track UUID' },
      { name: 'limit', type: 'number', required: false, description: 'Max items', defaultValue: 50 },
    ],
    responseDescription: 'Paginated operational alerts with timestamps, rules breached, and target track links.',
  },
  {
    id: 'alert_detail_get',
    domain: 'Intelligence & Defense',
    name: 'Alert Detail & Context',
    method: 'GET',
    path: '/alerts/{alert_id}',
    description: 'Query detailed alert payload, evaluation metadata, and target track linkage.',
    requiredPermission: 'alerts.read',
    pathParams: [
      { name: 'alert_id', type: 'string', required: true, description: 'UUID of the alert' },
    ],
    responseDescription: 'Alert record with severity, title, message, and contextual parameters.',
  },
  {
    id: 'threats_list_get',
    domain: 'Intelligence & Defense',
    name: 'Threat Priority Assessments',
    method: 'GET',
    path: '/threats',
    description: 'Query calculated threat assessments, threat levels, and deterministic scoring factors.',
    requiredPermission: 'threats.read',
    queryParams: [
      { name: 'level', type: 'string', required: false, description: 'Threat level (NONE, LOW, MEDIUM, HIGH, CRITICAL)' },
      { name: 'min_score', type: 'number', required: false, description: 'Minimum threat score threshold (0.0 - 1.0)' },
      { name: 'limit', type: 'number', required: false, description: 'Max items', defaultValue: 50 },
    ],
    responseDescription: 'Threat priority queue sorted by threat score and level.',
  },
  {
    id: 'threat_detail_get',
    domain: 'Intelligence & Defense',
    name: 'Track Threat Assessment',
    method: 'GET',
    path: '/threats/{track_id}',
    description: 'Query threat breakdown for a specific track, including proximity, speed, heading, and zone factors.',
    requiredPermission: 'threats.read',
    pathParams: [
      { name: 'track_id', type: 'string', required: true, description: 'UUID of the operational track' },
    ],
    responseDescription: 'Threat score (0-1), level classification, and contributing risk factors.',
  },
  {
    id: 'geofences_list_get',
    domain: 'Intelligence & Defense',
    name: 'List Defense Geofences',
    method: 'GET',
    path: '/geofences',
    description: 'List 2D bounding-box and polygon defense perimeters, inclusion/exclusion rules, and altitude bounds.',
    requiredPermission: 'scenarios.read',
    queryParams: [
      { name: 'enabled', type: 'boolean', required: false, description: 'Filter by active status' },
      { name: 'limit', type: 'number', required: false, description: 'Max items', defaultValue: 50 },
    ],
    responseDescription: 'Array of geofence geometries with bounding coordinates and altitude limits.',
  },
  {
    id: 'geofences_create_post',
    domain: 'Intelligence & Defense',
    name: 'Create Defense Geofence',
    method: 'POST',
    path: '/geofences',
    description: 'Register a new defensive perimeter with mathematical boundary validation.',
    requiredPermission: 'scenarios.create',
    requestBodySchema: 'GeofenceCreate',
    requestBodyTemplate: JSON.stringify(
      {
        name: 'Alpha Perimeter Zone',
        description: 'Primary defensive perimeter exclusion zone',
        enabled: true,
        min_altitude: 0,
        max_altitude: 500,
        rule: 'EXCLUSION',
        geometry: {
          type: 'BBOX',
          min_lat: 37.77,
          max_lat: 37.78,
          min_lon: -122.43,
          max_lon: -122.41,
        },
      },
      null,
      2
    ),
    responseDescription: 'Created geofence record with assigned UUID.',
  },

  // 6. Simulation & Scenarios
  {
    id: 'scenarios_list_get',
    domain: 'Simulation & Scenarios',
    name: 'List Scenario Configurations',
    method: 'GET',
    path: '/scenarios',
    description: 'List deterministic simulation scenarios, target drone configurations, and sensor models.',
    requiredPermission: 'scenarios.read',
    queryParams: [
      { name: 'limit', type: 'number', required: false, description: 'Max items', defaultValue: 50 },
    ],
    responseDescription: 'Array of scenario models with execution status (DRAFT, READY, RUNNING, PAUSED, COMPLETED).',
  },
  {
    id: 'scenario_detail_get',
    domain: 'Simulation & Scenarios',
    name: 'Scenario Configuration Detail',
    method: 'GET',
    path: '/scenarios/{scenario_id}',
    description: 'Query full scenario definition including targets, synthetic sensors, and defense zone linkages.',
    requiredPermission: 'scenarios.read',
    pathParams: [
      { name: 'scenario_id', type: 'string', required: true, description: 'UUID of the scenario' },
    ],
    responseDescription: 'Detailed scenario configuration and simulation state.',
  },
  {
    id: 'scenario_start_post',
    domain: 'Simulation & Scenarios',
    name: 'Start Simulation Execution',
    method: 'POST',
    path: '/scenarios/{scenario_id}/start',
    description: 'Start scenario simulation virtual clock and begin feeding synthetic observations into the pipeline.',
    requiredPermission: 'scenarios.run',
    pathParams: [
      { name: 'scenario_id', type: 'string', required: true, description: 'UUID of the scenario' },
    ],
    responseDescription: 'Simulation state transition confirmation.',
  },
  {
    id: 'scenario_step_post',
    domain: 'Simulation & Scenarios',
    name: 'Single Step Simulation Clock',
    method: 'POST',
    path: '/scenarios/{scenario_id}/step',
    description: 'Advance the deterministic virtual clock by one discrete simulation tick.',
    requiredPermission: 'scenarios.run',
    pathParams: [
      { name: 'scenario_id', type: 'string', required: true, description: 'UUID of the scenario' },
    ],
    responseDescription: 'Virtual clock timestamp and tick step result.',
  },
  {
    id: 'scenario_stop_post',
    domain: 'Simulation & Scenarios',
    name: 'Stop Simulation Execution',
    method: 'POST',
    path: '/scenarios/{scenario_id}/stop',
    description: 'Halt the active simulation scenario execution.',
    requiredPermission: 'scenarios.run',
    pathParams: [
      { name: 'scenario_id', type: 'string', required: true, description: 'UUID of the scenario' },
    ],
    responseDescription: 'Simulation stopped status.',
  },

  // 7. Historical & Analytics
  {
    id: 'history_timeline_get',
    domain: 'Historical & Analytics',
    name: 'Unified Operational Timeline',
    method: 'GET',
    path: '/history/timeline',
    description: 'Query aggregated operational events across detections, tracks, alerts, and threats with microsecond tie-breaking.',
    requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'],
    queryParams: [
      { name: 'time_from', type: 'string', required: false, description: 'ISO-8601 UTC start time filter' },
      { name: 'time_to', type: 'string', required: false, description: 'ISO-8601 UTC end time filter' },
      { name: 'event_types', type: 'string', required: false, description: 'Comma-separated event types (detection,track,alert,threat)' },
      { name: 'limit', type: 'number', required: false, description: 'Max events', defaultValue: 100 },
    ],
    responseDescription: 'Chronologically sorted timeline events with source IDs and payloads.',
  },
  {
    id: 'analytics_summary_get',
    domain: 'Historical & Analytics',
    name: 'Descriptive Analytics Summary',
    method: 'GET',
    path: '/analytics/summary',
    description: 'Retrieve system-wide descriptive counts and health KPIs across all operational subsystems.',
    requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'],
    responseDescription: 'Total counts of detections, tracks, alerts, threats, sensors, and scenarios.',
  },
  {
    id: 'analytics_tracks_get',
    domain: 'Historical & Analytics',
    name: 'Tracks Classification & Kinematics Analytics',
    method: 'GET',
    path: '/analytics/tracks',
    description: 'Aggregated analytics on track classifications, state distributions, speed histograms, and quality scores.',
    requiredPermission: 'tracks.read',
    queryParams: [
      { name: 'time_from', type: 'string', required: false, description: 'UTC start time filter' },
      { name: 'time_to', type: 'string', required: false, description: 'UTC end time filter' },
    ],
    responseDescription: 'Track classification breakdown, average quality, and kinematic distributions.',
  },
  {
    id: 'replay_query_post',
    domain: 'Historical & Analytics',
    name: 'Query Replay Time-Slice',
    method: 'POST',
    path: '/replay/query',
    description: 'Extract historical spatial snapshot of all active tracks and sensors at a specified point in time.',
    requiredAnyPermissions: ['scenarios.read', 'tracks.read', 'scenarios.run'],
    requestBodySchema: 'ReplayQueryRequest',
    requestBodyTemplate: JSON.stringify(
      {
        scenario_id: 'scenario-uuid',
        timestamp: new Date().toISOString(),
      },
      null,
      2
    ),
    responseDescription: 'Snapshot of active entity positions and kinematics at requested timestamp.',
  },

  // 8. Governance & RBAC
  {
    id: 'audit_events_get',
    domain: 'Governance & RBAC',
    name: 'Security Audit Ledger Explorer',
    method: 'GET',
    path: '/audit/events',
    description: 'Query the immutable, append-only security audit ledger with cursor-based pagination and filters.',
    requiredPermission: 'audit.read',
    queryParams: [
      { name: 'event_type', type: 'string', required: false, description: 'Audit event type (LOGIN_SUCCESS, ROLE_CREATED, etc.)' },
      { name: 'result', type: 'string', required: false, description: 'Outcome (SUCCESS, FAILURE)' },
      { name: 'actor_user_id', type: 'string', required: false, description: 'Actor User ID filter' },
      { name: 'limit', type: 'number', required: false, description: 'Page size (1-100)', defaultValue: 50 },
      { name: 'cursor', type: 'string', required: false, description: 'Cursor token for pagination' },
    ],
    responseDescription: 'Paginated audit events with timestamps, actor IDs, targets, and result codes.',
  },
  {
    id: 'roles_list_get',
    domain: 'Governance & RBAC',
    name: 'List RBAC Roles',
    method: 'GET',
    path: '/roles',
    description: 'List system-reserved and custom operational roles with assigned permissions.',
    requiredAnyPermissions: ['roles.read', 'permissions.read'],
    responseDescription: 'Array of roles with permissions, descriptions, and system immutability flags.',
  },
  {
    id: 'permissions_list_get',
    domain: 'Governance & RBAC',
    name: 'List System Permissions',
    method: 'GET',
    path: '/permissions',
    description: 'List all granular access permissions registered in the platform.',
    requiredAnyPermissions: ['permissions.read', 'roles.read'],
    responseDescription: 'Array of permissions grouped by resource domain and action.',
  },
];

export const DETECTION_PRESETS: DetectionIngestPreset[] = [
  {
    id: 'preset_radar_drone',
    name: 'High-Altitude Tactical Radar Drone',
    source_type: 'RADAR',
    description: 'Radar detection of a fast-moving small UAV with Doppler velocity and SNR metadata.',
    payload: {
      source_detection_id: `det-radar-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      latitude: 37.7749,
      longitude: -122.4194,
      altitude_m: 150.0,
      heading_deg: 85.0,
      speed_mps: 22.5,
      source_type: 'RADAR',
      confidence: 0.94,
      metadata: {
        snr_db: 21.3,
        rcs_dbsm: -8.5,
        doppler_hz: 1420.0,
        range_m: 3200.0,
      },
    },
  },
  {
    id: 'preset_rf_drone',
    name: 'RF Spectrum Emitter Detection',
    source_type: 'RF',
    description: 'RF detection identifying 2.4 GHz drone control and telemetry downlink signal.',
    payload: {
      source_detection_id: `det-rf-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      latitude: 37.7782,
      longitude: -122.4152,
      altitude_m: 85.0,
      heading_deg: 120.0,
      speed_mps: 14.0,
      source_type: 'RF',
      confidence: 0.88,
      metadata: {
        frequency_mhz: 2437.0,
        signal_strength_dbm: -64.2,
        protocol: 'OcuSync_3',
        bandwidth_mhz: 20.0,
      },
    },
  },
  {
    id: 'preset_optical_drone',
    name: 'EO/IR Optical Visual Classification',
    source_type: 'OPTICAL',
    description: 'Optical camera system identifying quadcopter rotary wing visual signature.',
    payload: {
      source_detection_id: `det-opt-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      latitude: 37.7712,
      longitude: -122.4225,
      altitude_m: 65.0,
      heading_deg: 260.0,
      speed_mps: 9.5,
      source_type: 'OPTICAL',
      confidence: 0.91,
      metadata: {
        camera_id: 'cam-ptz-north',
        bounding_box: [120, 340, 260, 480],
        visual_classification: 'ROTARY_WING_UAV',
        lighting_lux: 12000,
      },
    },
  },
];

export const SCHEMA_CATALOG: SchemaDefinition[] = [
  {
    name: 'RawDetection',
    domain: 'Sensor Ingestion',
    description: 'Canonical observation payload ingested from synthetic or hardware sensors.',
    fields: [
      { name: 'source_detection_id', type: 'string', required: true, description: 'Unique identifier from originating sensor', constraints: '1-64 characters' },
      { name: 'timestamp', type: 'string (ISO-8601 UTC)', required: true, description: 'Observation timestamp', constraints: 'Cannot be in future' },
      { name: 'latitude', type: 'number (float)', required: true, description: 'GPS latitude in decimal degrees', constraints: '[-90.0, 90.0]' },
      { name: 'longitude', type: 'number (float)', required: true, description: 'GPS longitude in decimal degrees', constraints: '[-180.0, 180.0]' },
      { name: 'altitude_m', type: 'number (float)', required: true, description: 'Altitude Above Ground Level in meters', constraints: '>= 0.0' },
      { name: 'heading_deg', type: 'number (float)', required: false, description: 'Compass heading in degrees clockwise from True North', constraints: '[0.0, 360.0)' },
      { name: 'speed_mps', type: 'number (float)', required: false, description: 'Horizontal ground speed in meters per second', constraints: '>= 0.0' },
      { name: 'source_type', type: 'string', required: true, description: 'Sensor modality classification', constraints: 'RADAR, RF, OPTICAL, ACOUSTIC' },
      { name: 'confidence', type: 'number (float)', required: true, description: 'Observation confidence rating', constraints: '[0.0, 1.0]' },
      { name: 'metadata', type: 'object', required: false, description: 'Modality-specific telemetry key-value dictionary' },
    ],
  },
  {
    name: 'TrackResponse',
    domain: 'Tracking & Fusion',
    description: 'Fused multi-sensor operational track state and kinematics.',
    fields: [
      { name: 'id', type: 'string (UUID)', required: true, description: 'Unique track identifier' },
      { name: 'state', type: 'string', required: true, description: 'Track lifecycle state', constraints: 'TENTATIVE, CONFIRMED, COASTING, CLOSED' },
      { name: 'classification', type: 'string', required: true, description: 'Target classification', constraints: 'DRONE, BIRD, AIRCRAFT, UNKNOWN' },
      { name: 'latitude', type: 'number', required: true, description: 'Current estimated latitude', constraints: '[-90.0, 90.0]' },
      { name: 'longitude', type: 'number', required: true, description: 'Current estimated longitude', constraints: '[-180.0, 180.0]' },
      { name: 'altitude_m', type: 'number', required: true, description: 'Current estimated altitude in meters', constraints: '>= 0.0' },
      { name: 'speed_mps', type: 'number', required: true, description: 'Estimated ground speed in m/s', constraints: '>= 0.0' },
      { name: 'heading_deg', type: 'number', required: true, description: 'Estimated heading in degrees', constraints: '[0.0, 360.0)' },
      { name: 'quality_score', type: 'number', required: true, description: 'Kinematic track quality score', constraints: '[0.0, 1.0]' },
      { name: 'source_count', type: 'number', required: true, description: 'Number of distinct contributing sensor systems', constraints: '>= 1' },
      { name: 'threat_level', type: 'string', required: false, description: 'Evaluated threat priority', constraints: 'NONE, LOW, MEDIUM, HIGH, CRITICAL' },
      { name: 'first_seen', type: 'string (ISO-8601 UTC)', required: true, description: 'Initial observation timestamp' },
      { name: 'last_seen', type: 'string (ISO-8601 UTC)', required: true, description: 'Most recent observation timestamp' },
    ],
  },
  {
    name: 'AlertResponse',
    domain: 'Intelligence & Defense',
    description: 'Operational alert record triggered by rules or perimeter breach.',
    fields: [
      { name: 'id', type: 'string (UUID)', required: true, description: 'Unique alert identifier' },
      { name: 'status', type: 'string', required: true, description: 'Alert lifecycle status', constraints: 'NEW, ACKNOWLEDGED, RESOLVED' },
      { name: 'severity', type: 'string', required: true, description: 'Severity classification', constraints: 'LOW, MEDIUM, HIGH, CRITICAL' },
      { name: 'type', type: 'string', required: true, description: 'Alert category rule', constraints: 'GEOFENCE_BREACH, PROXIMITY, SPEED, ANOMALY' },
      { name: 'title', type: 'string', required: true, description: 'Concise alert headline' },
      { name: 'message', type: 'string', required: true, description: 'Detailed diagnostic alert description' },
      { name: 'track_id', type: 'string (UUID)', required: false, description: 'Associated track ID if applicable' },
      { name: 'sensor_id', type: 'string (UUID)', required: false, description: 'Originating sensor ID if applicable' },
      { name: 'created_at', type: 'string (ISO-8601 UTC)', required: true, description: 'Alert creation timestamp' },
    ],
  },
  {
    name: 'ThreatResponse',
    domain: 'Intelligence & Defense',
    description: 'Deterministic threat assessment priority record.',
    fields: [
      { name: 'id', type: 'string (UUID)', required: true, description: 'Unique threat assessment identifier' },
      { name: 'track_id', type: 'string (UUID)', required: true, description: 'Target track UUID' },
      { name: 'level', type: 'string', required: true, description: 'Evaluated threat level', constraints: 'NONE, LOW, MEDIUM, HIGH, CRITICAL' },
      { name: 'score', type: 'number', required: true, description: 'Calculated threat score', constraints: '[0.0, 1.0]' },
      { name: 'proximity_factor', type: 'number', required: true, description: 'Distance risk factor weighting', constraints: '[0.0, 1.0]' },
      { name: 'speed_factor', type: 'number', required: true, description: 'Velocity risk factor weighting', constraints: '[0.0, 1.0]' },
      { name: 'heading_factor', type: 'number', required: true, description: 'Trajectory risk factor weighting', constraints: '[0.0, 1.0]' },
      { name: 'zone_factor', type: 'number', required: true, description: 'Geofence proximity risk factor', constraints: '[0.0, 1.0]' },
      { name: 'updated_at', type: 'string (ISO-8601 UTC)', required: true, description: 'Timestamp of last threat evaluation' },
    ],
  },
];

/**
 * Interpolate path variables in an API path string (e.g. /sensors/{sensor_id} -> /sensors/abc-123).
 */
export function interpolatePath(path: string, pathParams: Record<string, string> = {}): string {
  let result = path;
  for (const [key, value] of Object.entries(pathParams)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), encodeURIComponent(value));
  }
  return result;
}

/**
 * Format a key-value record into an encoded URL query string.
 */
export function buildQueryString(params: Record<string, string | number | boolean | undefined | null> = {}): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      searchParams.append(key, String(value));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : '';
}

/**
 * Generate a reproducible cURL CLI command formatted for PowerShell or POSIX bash.
 * Note: Never includes session tokens or raw credentials.
 */
export function generateCurlCommand(
  method: string,
  url: string,
  headers: Record<string, string> = {},
  body?: string,
  shell: 'powershell' | 'posix' = 'powershell'
): string {
  const isPostOrPut = ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase());
  const headerParts: string[] = [];

  for (const [key, value] of Object.entries(headers)) {
    headerParts.push(`-H "${key}: ${value}"`);
  }

  if (shell === 'powershell') {
    let cmd = `curl.exe -X ${method} "${url}"`;
    if (headerParts.length > 0) {
      cmd += ` ${headerParts.join(' ')}`;
    }
    if (isPostOrPut && body && body.trim()) {
      // Escape inner double quotes for PowerShell
      const escaped = body.replace(/"/g, '\\"');
      cmd += ` --data "${escaped}"`;
    }
    return cmd;
  }

  // POSIX bash
  let cmd = `curl -X ${method} '${url}'`;
  if (headerParts.length > 0) {
    cmd += ` ${headerParts.join(' ')}`;
  }
  if (isPostOrPut && body && body.trim()) {
    const escaped = body.replace(/'/g, `'\\''`);
    cmd += ` -d '${escaped}'`;
  }
  return cmd;
}

/**
 * Generate a ready-to-use JavaScript fetch() code snippet.
 */
export function generateFetchSnippet(
  method: string,
  url: string,
  headers: Record<string, string> = {},
  body?: string
): string {
  const isPostOrPut = ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase());
  const config: Record<string, unknown> = {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (isPostOrPut && body && body.trim()) {
    try {
      config.body = JSON.parse(body);
    } catch {
      config.body = body;
    }
  }

  const snippet = `const response = await fetch('${url}', {
  method: '${method}',
  credentials: 'include',
  headers: ${JSON.stringify(config.headers, null, 4).replace(/\n/g, '\n  ')}${
    isPostOrPut && body && body.trim()
      ? `,\n  body: JSON.stringify(${body.replace(/\n/g, '\n  ')})`
      : ''
  }
});
const data = await response.json();
console.log(data);`;

  return snippet;
}

/**
 * Validate synthetic sensor detection payload fields and coordinate bounds.
 */
export function validateDetectionPayload(payload: Record<string, unknown>): DetectionValidationResult {
  const errors: string[] = [];

  if (!payload || typeof payload !== 'object') {
    return { valid: false, errors: ['Payload must be a valid JSON object.'] };
  }

  // Required fields
  if (!payload.source_detection_id || typeof payload.source_detection_id !== 'string' || !payload.source_detection_id.trim()) {
    errors.push('Missing required field: source_detection_id (non-empty string).');
  }

  if (!payload.timestamp || typeof payload.timestamp !== 'string') {
    errors.push('Missing required field: timestamp (ISO-8601 string).');
  } else {
    const parsedDate = new Date(payload.timestamp);
    if (isNaN(parsedDate.getTime())) {
      errors.push('Invalid timestamp format: must be valid ISO-8601.');
    } else {
      const now = new Date();
      // Allow max 10 second clock drift for future check
      if (parsedDate.getTime() > now.getTime() + 10000) {
        errors.push('Timestamp cannot be in the future.');
      }
    }
  }

  // Coordinates
  if (typeof payload.latitude !== 'number' || isNaN(payload.latitude)) {
    errors.push('Missing or invalid latitude (must be a number).');
  } else if (payload.latitude < -90 || payload.latitude > 90) {
    errors.push('Latitude out of bounds: must be between -90.0 and 90.0 degrees.');
  }

  if (typeof payload.longitude !== 'number' || isNaN(payload.longitude)) {
    errors.push('Missing or invalid longitude (must be a number).');
  } else if (payload.longitude < -180 || payload.longitude > 180) {
    errors.push('Longitude out of bounds: must be between -180.0 and 180.0 degrees.');
  }

  if (typeof payload.altitude_m !== 'number' || isNaN(payload.altitude_m)) {
    errors.push('Missing or invalid altitude_m (must be a number).');
  } else if (payload.altitude_m < 0) {
    errors.push('Altitude out of bounds: altitude_m must be non-negative (>= 0.0).');
  }

  // Optional kinematics
  if (payload.speed_mps !== undefined && payload.speed_mps !== null) {
    if (typeof payload.speed_mps !== 'number' || isNaN(payload.speed_mps) || payload.speed_mps < 0) {
      errors.push('Speed out of bounds: speed_mps must be non-negative (>= 0.0).');
    }
  }

  if (payload.heading_deg !== undefined && payload.heading_deg !== null) {
    if (typeof payload.heading_deg !== 'number' || isNaN(payload.heading_deg) || payload.heading_deg < 0 || payload.heading_deg >= 360) {
      errors.push('Heading out of bounds: heading_deg must be in range [0.0, 360.0).');
    }
  }

  if (payload.confidence !== undefined && payload.confidence !== null) {
    if (typeof payload.confidence !== 'number' || isNaN(payload.confidence) || payload.confidence < 0 || payload.confidence > 1) {
      errors.push('Confidence out of bounds: must be between 0.0 and 1.0.');
    }
  }

  if (!payload.source_type || typeof payload.source_type !== 'string') {
    errors.push('Missing required field: source_type (RADAR, RF, OPTICAL).');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Dispatch an interactive API request through the browser with full telemetry timing and error extraction.
 */
export async function dispatchApiRequest(
  endpoint: ApiEndpoint,
  pathParams: Record<string, string> = {},
  queryParams: Record<string, string> = {},
  bodyJson?: string
): Promise<DispatchedResponse> {
  const resolvedPath = interpolatePath(endpoint.path, pathParams);
  const queryString = buildQueryString(queryParams);
  const fullUrl = `/api/v1${resolvedPath}${queryString}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const startTime = performance.now();

  try {
    const config: RequestInit = {
      method: endpoint.method,
      credentials: 'include',
      headers: defaultHeaders,
    };

    if (['POST', 'PUT', 'PATCH'].includes(endpoint.method) && bodyJson && bodyJson.trim()) {
      config.body = bodyJson;
    }

    const response = await fetch(fullUrl, config);
    const durationMs = Math.round(performance.now() - startTime);

    const headersRecord: Record<string, string> = {};
    response.headers.forEach((val, key) => {
      headersRecord[key] = val;
    });

    const correlationId = response.headers.get('x-correlation-id') || undefined;

    let responseData: unknown = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        responseData = await response.json();
      } catch {
        responseData = null;
      }
    } else {
      responseData = await response.text();
    }

    return {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: headersRecord,
      data: responseData,
      durationMs,
      correlationId,
    };
  } catch (err: unknown) {
    const durationMs = Math.round(performance.now() - startTime);
    const message = err instanceof Error ? err.message : 'Network execution failed';
    return {
      status: 0,
      statusText: 'Network Error',
      ok: false,
      headers: {},
      data: null,
      durationMs,
      error: message,
    };
  }
}

/**
 * Submit synthetic detection to backend ingestion endpoint.
 */
export async function ingestSyntheticDetection(
  sensorId: string,
  payload: Record<string, unknown>
): Promise<DetectionIngestionResult> {
  const url = `/api/v1/sensors/${encodeURIComponent(sensorId)}/detections`;
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = `Ingestion failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail);
  }

  return (await response.json()) as DetectionIngestionResult;
}
