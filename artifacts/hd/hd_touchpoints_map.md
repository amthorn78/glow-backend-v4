# Human Design Pins & Touchpoints Map

## Current Birth Data Storage

### birth_data table:
- **user_id**: integer (nullable: NO)
- **birth_date**: date (nullable: YES)
- **birth_time**: time without time zone (nullable: YES)
- **birth_location**: character varying (nullable: YES)
- **latitude**: numeric (nullable: YES)
- **longitude**: numeric (nullable: YES)
- **data_consent**: boolean (nullable: YES)
- **sharing_consent**: boolean (nullable: YES)
- **location_display_name**: text (nullable: YES)
- **location_country**: character varying (nullable: YES)
- **location_state**: character varying (nullable: YES)
- **location_city**: character varying (nullable: YES)
- **location_importance**: numeric (nullable: YES)
- **location_osm_id**: bigint (nullable: YES)
- **location_osm_type**: character varying (nullable: YES)
- **timezone**: character varying (nullable: YES)
- **location_source**: character varying (nullable: YES)
- **location_verified**: boolean (nullable: YES)

### Sample Structure (sanitized):
```json
{
  "user_id": "[USER_ID]",
  "birth_date": "1995-05-25",
  "birth_time": "14:35:00",
  "birth_location": "San Sebasti\u00e1n Airport, Gabarrari kalea, Amute-Kosta, Hondarribia, Bidasoa Beherea / Bajo Bidasoa, Gipuzkoa, Autonomous Community of the Basque Country, 20280, Spain",
  "latitude": "40.71272810",
  "longitude": "-74.00601520",
  "data_consent": false,
  "sharing_consent": false,
  "location_display_name": null,
  "location_country": null,
  "location_state": null,
  "location_city": null,
  "location_importance": null,
  "location_osm_id": null,
  "location_osm_type": null,
  "timezone": "America/New_York",
  "location_source": "manual",
  "location_verified": false
}
```

## HD-Related Tables

### human_design_data
- user_id: integer
- chart_data: text
- energy_type: character varying
- strategy: character varying
- authority: character varying
- profile: character varying
- api_response: text
- calculated_at: timestamp without time zone

### user_resonance_prefs
- user_id: integer
- version: integer
- weights: json
- facets: json
- created_at: timestamp without time zone
- updated_at: timestamp without time zone

### user_resonance_signals_private
- user_id: integer
- decision_mode: character varying
- interaction_mode: character varying
- connection_style: character varying
- bridges_count: smallint
- emotion_signal: boolean
- work_energy: boolean
- will_signal: boolean
- expression_signal: boolean
- mind_signal: boolean
- role_pattern: character varying
- tempo_pattern: character varying
- identity_openness: boolean
- trajectory_code: character varying
- confidence: json
- computed_at: timestamp without time zone

### compatibility_matrix
- user_a_id: integer
- user_b_id: integer
- love_score: smallint
- intimacy_score: smallint
- communication_score: smallint
- friendship_score: smallint
- collaboration_score: smallint
- lifestyle_score: smallint
- decisions_score: smallint
- support_score: smallint
- growth_score: smallint
- space_score: smallint
- overall_score: smallint
- calculated_at: timestamp without time zone

## Missing Pins for HD Engine

The following fields may need to be added for complete HD integration:

- **tzdb_version**: IANA timezone database version (e.g., '2025a')
- **geohash_8**: 8-character geohash for location precision
- **utc_instant**: Precise UTC timestamp of birth
- **fold**: DST fold indicator for ambiguous times
- **hd_chart_data**: Canonical HD chart calculations
