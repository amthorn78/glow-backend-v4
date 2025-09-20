# HD Integration Gaps & Proposals

## Current State Analysis

### Strengths
- ✅ Dedicated HD-related tables exist
- ✅ Birth data collection infrastructure in place
- ✅ User preferences system supports HD settings
- ✅ Compatibility matrix for matching calculations
- ✅ Resonance scoring system implemented

### Identified Gaps
- ⚠️ Missing timezone database version tracking
- ⚠️ No geohash indexing for location-based queries
- ⚠️ UTC instant calculation may need verification
- ⚠️ DST fold handling for ambiguous birth times
- ⚠️ Canonical HD chart storage vs. on-demand calculation

## Proposals for HD Engine Integration

### Phase 1: Data Enhancement
1. **Add timezone metadata fields** to birth_data table
2. **Implement geohash indexing** for efficient location queries
3. **Add UTC instant calculation** with DST fold handling

### Phase 2: Chart Storage Strategy
1. **Option A**: Store canonical HD charts in new `hd_canonical_charts` table
2. **Option B**: Calculate charts on-demand with caching layer
3. **Recommendation**: Hybrid approach - cache frequently accessed charts

### Phase 3: API Integration
1. **Deprecate direct humandesignapi.nl calls** from frontend
2. **Centralize HD calculations** in backend HD engine
3. **Implement HD data versioning** for schema evolution

## Migration Strategy

### Non-Breaking Changes (Immediate)
- Add new fields to existing tables with NULL defaults
- Implement geohash calculation for existing birth data
- Add timezone version tracking

### Breaking Changes (Planned)
- Modify compatibility_matrix structure if needed
- Update HD API response formats
- Consolidate resonance calculation methods

## Risk Assessment

### Low Risk
- Adding metadata fields to birth_data
- Implementing geohash indexing
- UTC instant calculation improvements

### Medium Risk
- Modifying compatibility_matrix schema
- Changing HD API response formats
- Migrating from external HD API to internal engine

### High Risk
- Complete HD calculation engine replacement
- Major schema restructuring
- Breaking changes to existing user data
