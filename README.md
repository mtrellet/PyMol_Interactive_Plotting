# PyMol_Interactive_Plotting

Multi-component architecture to bind PyMol molecular visualisation software and d3js plots of a molecular simulation parsed and stored in RDF format.

## REQUIREMENTS

- [Flask](http://flask.pocoo.org/docs/0.10/installation/) - `pip install flask`
- [Flask_Cors](https://pypi.python.org/pypi/Flask-Cors) - `pip install flask-cors`
- [Flask-SocketIO](https://flask-socketio.readthedocs.org/en/latest/) - `pip install flask-socketio`
- [Liblo](http://liblo.sourceforge.net/README.html) - `brew install liblo`
- [pyliblo](http://das.nasophon.de/pyliblo/) - `pip install pyliblo`
- [SPARQLWrapper](https://rdflib.github.io/sparqlwrapper/) - `pip install sparqlwrapper`


### 1. Start the Virtuoso server (RDF database)

`$> cd $VIRTUOSO_DB`

`$> virtuoso-t -f`

### 2. Launch PyMol in interactive mode

`$> pymol load_traj.pml`

Then in PyMol, click on:

`Plugins >> Distant interactive plots`

### 3. Launch Flask server (webserver)

Run 

`python app.py [OPTIONS]`

with 

`[OPTIONS]:
[-h] [--client_ip CLIENT_IP] [--client_port CLIENT_PORT]
[--server_ip SERVER_IP] [--server_port SERVER_PORT] [--ip IP]
[--port PORT] [--debug DEBUG]`

### 4. Access HTML interface

Go to 129.175.156.48:5000 or localhost:5000