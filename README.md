<a href="https://github.com/GreyPaperclip/cffa"><img src="https://lh3.googleusercontent.com/pw/ACtC-3emYHzct6Q9wvk-L7mp8MzrRDmTZaqoFJoUBLYBIUyEo7977-JQhekPDzZbzvOsHZzBVeQvi--2VsKjA5DMulSNeiZDvALGoxktsx0I1oONvsnRi3uKF9NmIzprwz_N6gz5ek3OnIZIM0oOFNu5jT-8=w828-h237-no" title="Casual Football Finance Manager" alt="CFFA"></a>

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

![Player View](https://lh3.googleusercontent.com/pw/ACtC-3dVwrHqBzUKZOW4c-PsoUzPMJmRbDhoSccWg2CbUE7K_8RYKLSJPNuHj8VsEkPAsjxDORbV1E1Z7Gp6EEMoL2uESI6bZeH7jn9ZT8qq7BGUHhSXiWhsQ0KteIflETRzpGP8eJW0PSYTjip7OykMfNoX=w576-h566-no)



Implemented using python, flask with bootstrap, wtforms with a mongodb backend. 

### Tutorials ###

a) end-to-end deployment on Raspberry Pi with Ubuntu 64bit server with mongoDB, python and nginx reverse proxy Docker containers :

[Raspberry PI containers]: https://github.com/GreyPaperclip/cffa/blob/master/Tutorials/RaspberryPI_deployment.md

b) scalable deployment on google cloud with kubernetes:

WIP

### Beta ###

The application is functional but requires more extensive testing for production use.

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

Create the .env file in the cffa directory

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
BACKEND_DBNAME=<MongoDB database name>

SECRET_KEY=<flask secret key used for flask encyption, for Dev env, for example use NotForProduction>
EXPORTDIRECTORY=absolute path to a temporary directory used for data exporting. Make sure this directory exists>
```

Prep virtual environment and start flask to listen on port 5000.

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
$ flask run --host 0.0.0.0 --cert .<your ssl crt file> --key <your ssl key file>
```

Log into the application:

![Log In](https://lh3.googleusercontent.com/pw/ACtC-3fSmp7A7M_0S6odC5mbar6u38Bvph12KuaC0VOH5RF67CmTgrpFLWrw2oQJdoZVEPObHSd3xTBkWOXgE1wFTzErnGTX8ch_5Jv_XN0tc0zG3B4dJknGHTmnMThXnR2GVspjQQaklp9N0pKJc6JX3Kef=w1043-h560-no)Enter your Auth0 CFFA user credentials:

[![Credentials](https://lh3.googleusercontent.com/pw/ACtC-3fv6Ey15V5DldKxW_tW8zNw-k2cJSwSPAxMIig723Xt86qRy2hxyqV8A3LjmjKTusZ7WFDtxcTezW0a0ULkoD5fsttp1405OPFePHnIsA8xiSshZBflkWwePSOqSTFvlMuwUDrkjcQmxQbcyugCN2te=w492-h573-no)]()

Onboarding screen - enter your team name:

[![Onboarding](https://lh3.googleusercontent.com/pw/ACtC-3f4m1WfFFDuh9Pjumpnc9pM_2AmqzDsaloWcOkgCnsuPlZYQ6i8Iz4LBZXMZh5oeJc6dQwfey4dy825HVLceF055meQYim1PBawHH1FG6kJM-cjRMo9bK9oskxkHlSkinwo2jFKhoYAFXr3JDBjhArX=w1156-h573-no)]()

No data yet!

[![No data](https://lh3.googleusercontent.com/pw/ACtC-3e2m-ON5I7-Xf6EP4R8qF0A227NMR9hhk30Bv9o2JI0axdSSL0oOZf2ppFiMw7PHtuKxUFh28i3LS7_xh9Ivew-oZZF0ka7OvhVRz-hgRONA-RJuuzmmB4sWg_EFzcWz1KOfnp6jFXMTX7LlsxzqyWG=w1156-h368-no)]()

Add some players

[![Add Player](https://lh3.googleusercontent.com/pw/ACtC-3c_vIuQLkHviXa23Y294TPWqvxylDitggSXL8M8TBpAiHLe5D5e7Vv3WJAwKWtmd7bO-OVDDgK_hJB9ibr0xG8qZgYk7TLJSUG_8b-t91aEiYcG6Mb7k_XMujMf_lqEhg-fZhKs_dwHeBAympiEdvaz=w1145-h333-no)]()

Log a game

[![Log Game](https://photos.google.com/share/AF1QipPtAGxyY1Hc7YOggtgwTCwK5z-yxXwG4rw2l9jUWZrIcfgDnC1HmKg7ioLW0vR-Ng/photo/AF1QipP5LeiWEuctRsxWMtunyXo1VKPrUWqRQsvO5PEq?key=NHZSeTdBVnVyVWVMLVF2LXRoeFJWNEhiZFFXaUlB)]()

Get Stats!

[![Get Stats](https://lh3.googleusercontent.com/pw/ACtC-3c5BYQXtNHc6CHo0FB3fFFVm5HUJWRgkuzy7JI_jFFogOE_V2hEBDvCFEwrAKmDgVIk5qsNKJdQvuhqwMCmbVhBsTyac98nTqBVBw_l245afwdrAxN3tAJR0atrcDfIS1s-bw9fuLz-DNKjlG44q6EG=w1154-h659-no)]()
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

- **Open to feedback!**
    - Please ask and I'll expand this section.

---

## Support

Twitter prefered: @rsborrett

---

## Credits ##

Implementation was influenced and inspired by https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world

Markcurtis1970 for the humour!

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

- **[MIT license](http://opensource.org/licenses/mit-license.php)**
- Copyright 2020 © Richard Borrett