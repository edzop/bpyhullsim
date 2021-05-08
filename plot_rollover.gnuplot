set datafile separator ','
dataFileName="bpyhullsim_hydro_rollover.csv"

stats dataFileName using 3 nooutput

max_weight=STATS_max

title_text=sprintf('bpyhullgen roll analysis - %0.0f kg',max_weight)

set title title_text

set xlabel "Heel Angle"
set ylabel "Righting Force"
#set xrange [0:180]

plot dataFileName using 9:($6) with lines title "Pitch Angle (Y)" lc rgb 'green', \
     dataFileName using 9:($10*100) with lines title "Pitch Arm (mm)" lc rgb 'dark-green', \
     dataFileName using 9:($7*100) with lines title "Roll Arm (mm)" lc rgb 'red'
