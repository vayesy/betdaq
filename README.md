# sportech-exchange-betdaq-stream-server
Implementation of Betdaq protocols (AAPI, GBEi) using Python language.

## Description
Betdaq exchange offers different services to its clients.  
`AAPI` & `GBEi` protocols are few of them to help clients operate with exchange data more efficiently.  
`AAPI` - built on top of WS, is used to receive exchange information about upcoming events and their details. Main goal is to quickly receive odds updates.  
`GBEi` - built on top of TCP, is used to efficiently process client orders to place bets.  
Repo implements those protocols in respective modules under `src` directory.  
Further usage and extension relies on the specific project which consumes those protocols.

### Installation
Requires python 3.7 or higher.
```bash
pip install -r requirements.txt
```
For testing:
```bash
pip install -r test-requiremenets.txt
```

### Running
Run AAPI base cient:
```bash
python -m betdaq.aapi
```

## Configuration:
All below configs can be provided via environment variables.

### AAPI
- ***BETDAQ_AAPI_STREAM_URL*** - url of Betdaq AAPI service.
- ***BETDAQ_AAPI_USERNAME*** - username to connect with. If not specified, anonymous session is established (if it's allowed on the server side).
- ***BETDAQ_AAPI_PASSWORD*** - password to connect with, related to the username config.
- ***BETDAQ_AAPI_REFRESH_PERIOD*** - frequency (in seconds) of price (odds) updates, sent by the server.
- ***BETDAQ_AAPI_META_REFRESH_PERIOD*** - frequency (in seconds) of metadata (like event lists, start times etc.) updates.
- ***BETDAQ_AAPI_PRICES_NUMBER*** - Number of best back/lay prices to receive.

### GBEi
- ***BETDAQ_GBEI_URL*** - url of Betdaq GBEi service.
- ***BETDAQ_GBEI_PUNTER_ID*** - punter id (or username) to connect to the service. Anonymous connection is not allowed.
- ***BETDAQ_GBEI_PUNTER_SESSION_KEY*** - session key, related to given user.

### Tests
Tests are written with pytest library.
To run tests, use next command:
```bash
python -m pytest
```
