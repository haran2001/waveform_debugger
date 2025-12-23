# Debug Report: wfull Assertion Failure

## Summary
The investigation found that the `wfull` signal behaves correctly according to the design logic, asserting high at `t=325000`. The failure reported ("wfull never asserted") is caused by the testbench sampling the signal at the clock edge before the new value propagates (Race condition/Sampling issue).

## Root Cause Analysis
The FIFO logic is designed with a registered `wfull` output.
- **Design Behavior:** `wfull` is updated on the rising edge of `wclk`.
- **Timing at Failure:**
    - At `t=315000` (cycle N-1): `wbin` updates to 14. The combinational "next" logic detects that the *next* write (to 15) will make the FIFO full (Depth 8, Read Ptr 7). `wfull_val` (next state) goes high.
    - At `t=325000` (cycle N): `wclk` rises. The flip-flop for `wfull` captures `wfull_val` (1) and transitions `wfull` from 0 to 1.
- **Testbench Issue:** The testbench expects `wfull=1` *at* `t=325000`. If the check is performed synchronously on the clock edge (e.g., `@(posedge wclk)`), it samples the value *before* the update (which is 0).

## Signal Trace
| Time | Signal | Value | Note |
|---|---|---|---|
| 315000 | `wclk` | 1 (Rise) | Write to wbin=14 |
| 315000 | `wfull_val` | 1 | Full condition detected for next cycle |
| 315000 | `wfull` | 0 | Latches previous val (0) |
| 325000 | `wclk` | 1 (Rise) | Write to wbin=15 |
| 325000 | `wfull` | **1** | Latches wfull_val (1) - **Transitions High Here** |

## Recommendation
The FIFO design is functioning correctly (Full flag asserts when occupancy reaches 8).
To fix the testbench failure, adjust the sampling logic:
1.  **Sample on Negedge:** Check `wfull` on the falling edge of `wclk`.
2.  **Add Delay:** Wait for a small delay after the clock edge before checking.
3.  **Check Combinational:** If zero-latency full detection is required (unlikely for Async FIFO), check `wfull_val`.
