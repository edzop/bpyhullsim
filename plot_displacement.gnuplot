set datafile separator ','
dataFileName="bpyhullsim_hydro_submerge.csv"

plot dataFileName using 1:3 with lines title 'Displacement (KG)', \
        dataFileName using 1:($5*100) with lines title "Depth (CM)"
