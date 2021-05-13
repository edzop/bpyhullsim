set datafile separator ','
dataFileName="bpyhullsim_hydro_submerge.csv"

plot dataFileName using 1:4 with lines title 'Displacement (KG)', \
        dataFileName using 1:($6*100) with lines title "Depth (CM)"
