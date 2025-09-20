# Database Schema Overview - BE-AUD-DB-01

**Generated:** 2025-09-20T22:43:13Z  
**Database:** PostgreSQL 17.6  
**Total Tables:** 12  

## Table Summary

| Table | Rows | Purpose | HD Related |
|-------|------|---------|------------|
| users | 5 | Core user accounts | ✅ |
| birth_data | 1 | Birth pins for HD calculations | ✅ |
| human_design_data | 0 | HD chart calculations | ✅ |
| user_resonance_prefs | 0 | Resonance weights/facets | ✅ |
| user_resonance_signals_private | 0 | Private HD signals | ✅ |
| compatibility_matrix | 0 | Magic-10 scoring | ✅ |
| user_preferences | 1 | User settings (preferred_pace) | ❌ |
| user_profiles | 0 | Profile data | ❌ |
| user_priorities | 0 | Priority settings | ❌ |
| user_sessions | 0 | Session management | ❌ |
| email_notifications | 0 | Email settings | ❌ |
| admin_action_log | 0 | Admin audit trail | ❌ |

## HD Engine Integration Status

### Current Birth Pins ✅
- birth_date, birth_time, timezone (IANA)
- latitude, longitude (numeric precision)
- location_display_name with full address
- Consent tracking (data_consent, sharing_consent)

### Missing Pins ⚠️
- tzdb_version (timezone database version)
- geohash_8 (location indexing)
- utc_instant (precise UTC birth moment)
- fold (DST ambiguity resolution)

### HD Tables Present ✅
- human_design_data (core calculations)
- user_resonance_prefs (weights/facets)
- user_resonance_signals_private (private signals)
- compatibility_matrix (Magic-10 scores)

## Files Generated
- `schema.sql` - Complete DDL (184 lines)
- `tables/` - Individual table descriptions (12 files)
- `tables.csv` - Foreign key relationships
- `samples/` - Sanitized HD table samples (PII-free)

## Next Steps
1. Add missing pins to birth_data table
2. Implement HD engine canonical adapter
3. Migrate from external HD API to internal calculations
