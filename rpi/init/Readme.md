To run these scripts as daemons on Raspian start-up do:

    sudo cp ./hadoop-summit-cooltech-temperature.sh /etc/init.d
    sudo cp ./hadoop-summit-cooltech-voting.sh /etc/init.d

and ensure

    sudo chmod 755 /etc/init.d/hadoop-summit-cooltech-temperature.sh
    sudo chmod 755 /etc/init.d/hadoop-summit-cooltech-voting.sh