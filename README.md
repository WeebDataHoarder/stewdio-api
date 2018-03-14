# Stewdio API

Stewdio API is the central piece of the Stewdio Radio System (SRS). It provides searching and requesting functionality to users and queues songs with the actual streaming daemon (currently only supporting [kawa](https://github.com/Luminarys/kawa)).


## Setup

Install, configure in /etc/stewdio/api.conf, initialize database with alembic, run.



## Restricted API endpoints
Some restricted API endpoints require an account. Currently, that only includes adding and removing favorites for a user that has a password set.


### Setting a password on users without password
If a user was created without a password, a password can only be set using CLI interface. This will generate a random password that can be reset using the *user update* endpoint.

```sh
python -m stewdio.user <username>
```


### Creating a user
If no user exists yet, it can be created via the `/api/user/creatwe` endpoint:

```sh
curl 'http://localhost:5000/api/user/create' --user minus:asdf -XPOST -s | jq
```


### Authenticating to user management endpoints
Endpoints under `/api/user` require authenticating with [HTTP Basic Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication), i.e. username and password must be sent in the `Authorization` header.


### Changing a user password
To change a user's password, send a request with the new password to the `/api/user/update` endpoint:

```sh
curl 'http://localhost:5000/api/user/create' --user minus:asdf -d '{"password":"newasdf"}' -s | jq
```


### Creating API keys
Some endpoints require an API key. One can be created using the `/api/user/apikeys/create` endpoint by supplying a name for the key (purely informational). The response will contain the API key in the `key` field in the object in the `key` field. This key is just shown once.

```sh
curl 'http://localhost:5000/api/user/apikeys/create' --user minus:asdf -d '{"name":"cli request script"}' -s | jq .key.key
```


### Authenticating to other endpoints
Some endpoints, like adding and removing favorites, require an API key to be supplied. The user/password credentials are not accepted. The API key can either be passed via a GET parameter `apikey`, or in the `Authorization` header as *Basic authentication*. Adding the current song to favorites looks as follows:

```sh
curl 'http://localhost:5000/api/favorites/minus/playing' --user '<api key>:' -XPUT
curl 'http://localhost:5000/api/favorites/minus/playing' --user 'anything:<api key>' -XPUT
curl 'http://localhost:5000/api/favorites/minus/playing?apikey=<api key>' -XPUT
```
