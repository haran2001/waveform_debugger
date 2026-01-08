# Debug Report: FIFO Data Overflow

## Root Cause Summary
The testbench fails to respect the `wfull` (write full) flag, causing a data overflow.
Specifically, the testbench enters a phase where it stops reading (`rinc=0`) but continues to write blindly for 11 cycles, exceeding the FIFO depth of 8.

The user's observation "wfull never asserted" is incorrect; the signal **does** assert at time 325,000, but the testbench continues to drive `winc` high for several more cycles, ignoring the flag.

## Detailed Trace Analysis

1.  **Reset Phase (0 - 80,000):**
    *   System is in reset (`wrst_n=1` -> `0` -> `1`).
    *   Reset is effectively released at time 80,000.

2.  **Normal Operation Phase (80,000 - 280,000):**
    *   Writes (`winc`) and Reads (`rinc`) are both active.
    *   Rates are balanced (one operation every 20,000 time units).
    *   Loop variable `i` counts 0 to 9.

3.  **Overflow Phase (280,000 - 390,000):**
    *   **280,000:** Reads stop (`rinc` goes to 0). Writes continue.
    *   **325,000:** FIFO fills up. **`wfull` asserts (goes to 1).**
    *   **325,000 - 390,000:** `wfull` remains high, but `winc` continues to toggle (is asserted).
    *   Loop variable `i` counts 0 to 10 (11 writes), ignoring the full state.
    *   The testbench attempts to write to a full FIFO multiple times, triggering the "data overflow" error.

## Signal Evidence
| Time | Signal | Value | Note |
|---|---|---|---|
| 280,000 | `rinc` | 0 | Reads stop |
| 280,000 | `winc` | 1 | Writes continue (start of loop) |
| 325,000 | `wfull` | **1** | **FIFO indicates FULL** |
| 335,000 | `winc` | 1 | Testbench writes anyway (Overflow) |
| 345,000 | `winc` | 1 | Testbench writes anyway (Overflow) |
| 390,000 | `winc` | 0 | Loop finishes |

## Recommended Fix
Modify the testbench write loop to check `wfull` before asserting `winc`.

**Current Logic (Inferred):**
```verilog
for (i = 0; i < 11; i = i + 1) begin
    @(posedge wclk);
    winc = 1; // Blind write
    // ...
end
```

**Corrected Logic:**
```verilog
for (i = 0; i < 11; i = i + 1) begin
    @(posedge wclk);
    while (wfull) @(posedge wclk); // Wait if full
    winc = 1;
    // ...
end
```
