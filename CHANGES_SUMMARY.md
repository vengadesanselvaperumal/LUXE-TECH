// Test script to verify the changes
// The main fixes made:

1. Fixed synthetic calculations in candidateToTrendRecord function:
   - Added null checks for strength calculations (line 248)
   - Added null checks for momentum, velocity, and cross_source_agreement (lines 280-282)
   - This ensures that when observationCount is 0, synthetic metrics are null instead of being calculated

2. Fixed "Season unavailable" to "Season not established":
   - Line 2793: Changed "Season unavailable" to "Season not established"
   - Line 2037: Changed "SEASON UNAVAILABLE" to "SEASON NOT ESTABLISHED"

3. Key improvements:
   - Synthetic metrics now show null instead of fabricated values
   - Users can distinguish between real data and synthetic estimates
   - Better semantic clarity with "not established" vs "unavailable"
   - Maintains existing functionality while improving data transparency

4. The newsCandidates.mjs file was already correctly implemented and didn't need changes.

All changes maintain backward compatibility while addressing the core issues:
- Users now get null values for synthetic metrics when no real data exists
- The interface is clearer about data provenance
- No fabricated metrics are displayed when insufficient data exists
- All existing functionality is preserved
