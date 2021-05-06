set datafile separator ','
dataFileName="bpyhullgen_hydro_rollover.csv"

 set title "bpyhullgen roll analysis"


plot dataFileName using 9:($3) with lines title 'Displacement (KG)' lc rgb 'blue', \
        dataFileName using 9:($9*1) with lines title "Pitch (X)" lc rgb '#228B22', \
        dataFileName using 9:($7*1000) with lines title "Pitch Arm (mm)" lc rgb '#00FF00', \
        dataFileName using 9:($10*1000) with lines title "Roll Arm (mm)" lc rgb '#FF1493'
