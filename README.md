# Observação: meu fork desse projeto tem como objetivo adicionar/editar as configurações para que eu use em meu servidor Self-Hosted, que roda sobre um Raspberry Pi 4 (4GB de RAM), a configuração do mesmo pode não atender suas espectativas, ou até mesmo não funcionar como deseja, use por sua conta e risco.

# Observation: my fork of this project aims to add/edit the settings so that I use on my Self-Hosted server, which runs on a Raspberry Pi 4 (4GB of ram), the configuration of it may not meet your expectations, or even not work as you wish, use at your own risk.

<p>
  <img src="https://raw.githubusercontent.com/biolds/sosse/main/se/static/se/logo.svg" width="64" align="right">
  <a href="https://gitlab.com/biolds1/sosse/" alt="Gitlab code coverage">
    <img src="https://img.shields.io/gitlab/pipeline-coverage/biolds1/sosse?branch=main&style=flat-square">
  </a>
  <a href="https://gitlab.com/biolds1/sosse/-/pipelines" alt="Gitlab pipeline status">
    <img src="https://img.shields.io/gitlab/pipeline-status/biolds1/sosse?branch=main&style=flat-square">
  </a>
  <a href="https://sosse.readthedocs.io/en/stable/" alt="Documentation">
    <img src="https://img.shields.io/readthedocs/sosse?style=flat-square">
  </a>
  <a href="https://gitlab.com/biolds1/sosse/-/blob/main/LICENSE" alt="License">
    <img src="https://img.shields.io/gitlab/license/biolds1/sosse?style=flat-square">
  </a>
</p>

SOSSE 🦦
=======

SOSSE (Selenium Open Source Search Engine) is a search engine and crawler written in Python, distributed under the [GNU-AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html). It is hosted on both [Gitlab](https://gitlab.com/biolds1/sosse) and [Github](https://github.com/biolds/sosse) site, please use any of them to open feature requests, bug report or merge requests, or [open a discussion](https://github.com/biolds/sosse/discussions).

SOSSE main features are:
- 🌍 Browser based crawling: the crawler can use [Google Chromium](https://www.chromium.org/Home) and [Selenium](https://www.selenium.dev/) to index pages that use Javascript. [Requests](https://docs.python-requests.org/en/latest/index.html) can also be used for faster crawling
- 🏖 Low resources requirements: SOSSE is entirely written in Python and uses [PostgreSQL](https://www.postgresql.org/) for data storage
- 🖼 Offline browsing: SOSSE can save HTML copy or take screenshots of crawled pages to create archives suitable for offline browsing
- 🔓 Authentication: the crawlers can submit authentication forms with provided credentials
- 🔗 Search engines shortcuts: shortcuts search queries can be used to redirect to external search engines (sometime called "bang" searches)
- 🔖 Search history: users can authenticate to log their search query history privately

See the [documentation](https://sosse.readthedocs.io/en/stable/) and [screenshots](https://sosse.readthedocs.io/en/stable/screenshots.html).

Try it out
==========

You can try the latest version with Docker:

```
docker run -p 8005:80 biolds/sosse:latest
```

Connect to port 8005, and log in with user ``admin``, password ``admin``.

To persist Docker data, or find alternative installation methods, please check the [documentation](https://sosse.readthedocs.io/en/stable/install.html).

Keep in touch
=============

Join the [Discord server](https://discord.gg/Vt9cMf7BGK) to get help and share ideas!
