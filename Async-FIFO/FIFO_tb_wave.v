`timescale 1ns/1ps

module FIFO_tb_wave();

    parameter DSIZE = 8;
    parameter ASIZE = 3;
    parameter DEPTH = 1 << ASIZE;

    reg [DSIZE-1:0] wdata;
    wire [DSIZE-1:0] rdata;
    wire wfull, rempty;
    reg winc, rinc, wclk, rclk, wrst_n, rrst_n;

    FIFO #(DSIZE, ASIZE) fifo (
        .rdata(rdata), 
        .wdata(wdata),
        .wfull(wfull),
        .rempty(rempty),
        .winc(winc), 
        .rinc(rinc), 
        .wclk(wclk), 
        .rclk(rclk), 
        .wrst_n(wrst_n), 
        .rrst_n(rrst_n)
    );

    integer i=0;
    integer seed = 1;

    always #5 wclk = ~wclk;
    always #10 rclk = ~rclk;
    
    initial begin
        //$dumpfile("fifo_wave.vcd");
        $dumpfile("fifo_wave_bug.vcd");
        $dumpvars(0, FIFO_tb_wave);
        
        wclk = 0; rclk = 0;
        wrst_n = 1; rrst_n = 1;
        winc = 0; rinc = 0; wdata = 0;

        #40 wrst_n = 0; rrst_n = 0;
        #40 wrst_n = 1; rrst_n = 1;

        // TEST 1: Write and read
        rinc = 1;
        for (i = 0; i < 10; i = i + 1) begin
            wdata = $random(seed) % 256;
            winc = 1; #10; winc = 0; #10;
        end

        // TEST 2: Fill FIFO
        rinc = 0; winc = 1;
        for (i = 0; i < DEPTH + 3; i = i + 1) begin
            wdata = $random(seed) % 256; #10;
        end

        // TEST 3: Empty FIFO
        winc = 0; rinc = 1;
        for (i = 0; i < DEPTH + 3; i = i + 1) #20;

        $finish;
    end
endmodule
