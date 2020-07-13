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
EXPORTDIRECTORY=absolute path to a temporary directory used for data exporting. Make sure this directory exists>
```

> Prep virtual environment and start flask to listen on port 5000.

```shell
$ python3 -m venv <path to your virtual cffa environment>
$ source bin/activate
$ cd <your cffa directory>
$ pip3 install --upgrade pip
$ pip3 install -r requirements.txt 
$ [double check your .env file.
$ export FLASK_APP=server.py
$ export FLASK_ENV=development
$ export PYTHONPATH=<path_to_parent_dir_of_cffadb_and_path_to_cffa_directory>
$ flask run --host 0.0.0.0 --cert .<your ssl crt file> --key <your ssl key pem file>
```

> Log into the application:

[![](https://lh3.googleusercontent.com/pw/ACtC-3dBOerh6lT5EpI_pobsP63-EDducO5XoF2pZDt_jEmptzMj9NtIdgU9TMq7k4IXHhWthjfOVT-nxf1Yyf-zYaJ24JZbwM0Y5AbBk5UJLkF1-DktSI12o4Vx3lnXAzKwoi_nEeE81AFATgcBH6gOz4Gp=w1043-h560-no?authuser=0)]()

> Enter your Auth0 CFFA user credentials:

[![](https://lh3.googleusercontent.com/pw/ACtC-3eRtCVF2hv9HvR3-GJyTMlDko4lXWO619Km83MCYR-mBVR_1rDJvFZNUKd3fHRjun5VkPo1GoXDwx1aYS2JynLnFqckr9kXv2llAqb8-_M8QY6EmASTPUeteonj5YsdLJ1EUHUDtyNAyvDvHnpwD0_r=w492-h573-no?authuser=0)]()

> Onboarding screen - enter your team name:

[![](https://lh3.googleusercontent.com/pw/ACtC-3e3q2pb5YQVOOlZsrb5gCoGRXCQXVJMr0xxULSf6RREQNuWPwvxAQofIXP8-5pwY4LtMfAWp2D6cYDsi7JRr5JncBhKieF77-bBl5cyMuHpNy0BJDdikrBnelk4gNUBNvL9av-xnGLrOnQ1Ws9SecVh=w1156-h573-no?authuser=0)]()

> No data yet!

[![](https://lh3.googleusercontent.com/pw/ACtC-3cHMZnTLEeuVjX1oC7jMZqDsXzV4Nn_o0btZpCu54Sd_BEf-l7gtfiI-R6NZhxG3a3oZ89_-q5a17l1yCMOGAEAPcuDrVb50bQ4g1CQFrhJD5BCLfema9Acpz3XRMX7zlVqng3jFzA2NhvNrN7pCLZM=w1156-h368-no?authuser=0)]()

> Add some players

[![](https://lh3.googleusercontent.com/pw/ACtC-3cHipcS0K0yZjKEU8YTCs5QyIvN9gK4gJ5_ZxGjagHn_ejeFfODjoN9kRes4cYu7MojVq_-G0smWBkMHh-5YEnOgBBQV5LL_DBbOAwoRQsPZfFMjJiGhEvKP4poYBr6uXgAKH4NeW3Eqiu54LcIdncJ=w1145-h333-no?authuser=0)]()

> Log a game

[![](https://lh3.googleusercontent.com/pw/ACtC-3cUQmBdcfJ9YHovm25Oi-z6mgw7pu0cl7YqxBkXLIP7s5SNuYAt8oamo8A3obS0sOYVn0kLikmLP-3qAej2gDvXpKgSkntf-jspB2e62_f5CzQhEPr9X9iwcx4FdAyxjzC2UZy3pfeKbOPqZvswRhkk=w1154-h659-no?authuser=0)]()

> Get Stats!

[![](https://lh3.googleusercontent.com/pw/ACtC-3cQC28HXbqWCl6ZxXQ8gmJagLIC71I0BvHvGZUJnObk1CAJsUEKCIozjGyzYd2W4ntkkrTvJZDzUBeWkjosMauqIz1Ax34eOmCqwYdnwK1hU39bPZEASgxtwwQ0M0oHoWJxOvJYWbQDCj1EUj1FxNo2=w1158-h491-no?authuser=0)]()
---



## Features

* Track sports games on a frequent or infrequent basis and log who played the same, and the booking cost.
* Charge each attending playing the portion of the booking cost
* A player can bring un-named guests (the player takes the guest portion of the cost)
* Correct incorrectly entered games
* Add, edit, retire players
* Add transactions to cover cash, bank transfer or other payments
* Review past games and transactions.
* Manage user access. Managers have full access to functionality. Players can only see their balances and key stats
* Import historical data from google sheet. Example data here: 
⋅⋅⋅https://docs.google.com/spreadsheets/d/1JDQ2vMr8q9ldu89m0TC0lus7X6hbeKt7OQGFMNfBjlo/edit?usp=sharing
* Reset database and start over.
* Export and download data (JSON format)
* Dark mode Web interface supports mobile and desktop views.
* Strong security with Auth0 integration

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