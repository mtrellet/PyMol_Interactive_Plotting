# PyMol_Interactive_Plotting

Multi-component architecture to bind PyMol molecular visualisation software and d3js plots of a molecular simulation parsed and stored in RDF format.

## 1. Start the Virtuoso server (RDF database)

`$> cd $VIRTUOSO_DB`

`$> virtuoso-t -f`

## 2. Launch PyMol in interactive mode

`$> pymol load_traj.pml`

Then in PyMol, click on:

`Plugins >> Distant interactive plots`

## 3. Launch Flask server (webserver)

Run 

`python app.py [OPTIONS]`

with 

`[OPTIONS]:
[-h] [--client_ip CLIENT_IP] [--client_port CLIENT_PORT]
[--server_ip SERVER_IP] [--server_port SERVER_PORT] [--ip IP]
[--port PORT] [--debug DEBUG]`

## 4. Enjoy !
