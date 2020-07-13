<a href="https://github.com/GreyPaperclip/cffa"><img src="https://mafm.richardborrett.com/static/mafm_backdrop.jpg" title="Casual Football Finance Manager" alt="CFFA"></a>

<!-- [![Richard Borrett](https://github.com/GreyPaperclip/cffa)](https://github.com/GreyPaperclip/cffa) -->


# Casual Football Finance Administrator 

> A Web application to help manage non-subscription sport team finances

> More serious/committed sports teams will use subscriptions to charge players on a regular basis. For example
>a manager will ask for £20 a month to cover a weekly block pitch booking. If a player can't make a game, they forfeit the 
>cost. 
>
>This application manages a more casual arrangement and track costs where games go ahead on an ad-hoc basis, when a booking
>is made only when enough players can confirm they can make it. 
>
>The application provides two views:

Manager View - see how much is owed by who, input games, add transactions, add/remove players etc

![Recordit GIF](http://recordit.co/lrvWjVrr0w.gif)

Player View - see how much they owe the manager and a summary of their playing and payment history

[![](https://mafm.richardborrett.com/static/examplePlayerScreen.png)]()



> --

> Implemented using python, flask with bootstrap, wtforms with a mongodb backend. 
>Tutorials include:
>
>a) deployment on Raspberry Pi with Ubuntu 64bit server with Docker containers 
>
>b) scalable deployment on google cloud with kubernetes

>> Status: Beta. The application is functional but requires more extensive testing for production use.
>

## Table of Contents

- [Installation](#installation)
- [Features](#features)
- [Contributing](#contributing)
- [Team](#team)
- [FAQ](#faq)
- [Support](#support)
- [License](#license)


---

---

## Installation

- Set up a mongoDB instance
- Install python3 and pip3
- Sign up to Auth0 (free tier is enough) and create a new single page app and your user to log in. TIP: make sure you change the Auth0
name from email address to your name
- Have some signed or self signed certificates (.pem and .crt) for https support.
- FOr Auth0 authentication to work, your domain will need to route to the flask server. In a home setting you will need
to set the router to forward traffic to the flask port 5000. NB: This does not need to be the https port. For example
https://cffa.your.com:444 can work, provided cffa.yourwebsite.com DNS A record forwards to your [static] external IP address, 
and your home router is set up to forward tcp traffic incoming on port 444 to port 5000 on your flask server.

### Clone

- Clone these repos to your local machine using `https://github.com/GreyPaperclip/cffa` and 
`https://github.com/GreyPaperclip/cffadb`

### Simple Development Setup

> Create the .env file in the cffa directory

```shell
AUTH0_CLIENT_ID=<your Auth0 App Client ID>
AUTH0_DOMAIN=<your Auth0 domain, will be *.*.auth0.com>
AUTH0_CLIENT_SECRET=<your Auth0 App Client Secret>
AUTH0_CALLBACK_URL=https://your_domain:your_server_port/callback
AUTH0_AUDIENCE=https://<your Auth0 domain>/userinfo

BACKEND_DBPWD=<your MongoDB password for your football DB instance>
BACKEND_DBUSR=<your MongoDB username for your football DB instance>
BACKEND_DBHOST=<your MongoDB IP(s), hostname(s) comma separated>
BACKEND_DBPORT=<your MongoDB port number, often 27017>
BACKEND_DBNAME=MongoDB database name>

SECRET_KEY=<flask secret key used for flask encyption, for Dev env, for example use NotForProduction>
PYTHONPATH=<absolute path to the cffa code dirctory: absolute path to the cffadb directory>
EXPORTDIRECTORY=absolute path to a temporary directory used for data exporting>
```

> Prep virtual environment and start flask to listen on port 5000.

```shell
$ python3 -m venv <path to your virtual cffa environment>
$ cd <your cffa directory>
$ pip3 install -r requirements.txt 
$ export FLASK_APP=server.py
$ export FLASK_ENV=development
$ flask run --host 0.0.0.0 --cert .<your ssl crt file> --key <your ssl key pem file>
```

---

## Features

> Track sports games on a frequent or infrequent basis and log who played the same, and the booking cost.
> Charge each attending playing the portion of the booking cost
> A player can bring un-named guests (the player takes the guest portion of the cost)
> Correct incorrectly entered games
> Add, edit, retire players
> Add transactions to cover cash, bank transfer or other payments
> Review past games and transactions.
> Manage user access. Managers have full access to functionality. Players can only see their balances and key stats
> Import historical data from google sheet. Example data here: 
>https://docs.google.com/spreadsheets/d/1JDQ2vMr8q9ldu89m0TC0lus7X6hbeKt7OQGFMNfBjlo/edit?usp=sharing
> Reset database and start over.
> Export and download data (JSON format)
> Dark mode Web interface supports mobile and desktop views.
> Strong security with Auth0 integration

---

## Contributing

> All welcome to fork or clone this repo.
---

## Team

> Richard Borrett, cffa@richardborrett.com / Twitter: @rsborrett

---

## FAQ

- **How do I do *specifically* so and so?**
    - Please ask and I'll expand this section.

---

## Support

Twitter prefered: @rsborrett

---

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

- **[MIT license](http://opensource.org/licenses/mit-license.php)**
- Copyright 2020 © Richard Borrett