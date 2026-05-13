

[![CodeFactor](https://www.codefactor.io/repository/github/nlr-distribution-suite/erad/badge)](https://www.codefactor.io/repository/github/nlr-distribution-suite/erad) • [![codecov](https://codecov.io/gh/NLR-Distribution-Suite/erad/graph/badge.svg?token=FtAWhS5svb)](https://codecov.io/gh/NLR-Distribution-Suite/erad) • [![GitHub license](https://img.shields.io/github/license/NREL/erad)](https://github.com/NREL/erad/blob/main/LICENSE.txt) • [![GitHub issues](https://img.shields.io/github/issues/NREL/erad)](https://github.com/NREL/erad/issues) • ![PyPI - Downloads](https://img.shields.io/pypi/dm/NREL-erad) • [![Upload to PyPi](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/publish.yml/badge.svg)](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/publish.yml) • [![deploy-book](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/deploy.yml/badge.svg)](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/deploy.yml) • [![Pytest](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/pull_request_tests.yml/badge.svg)](https://github.com/NLR-Distribution-Suite/erad/actions/workflows/pull_request_tests.yml) • [![DOI](https://joss.theoj.org/papers/10.21105/joss.08782/status.svg)](https://doi.org/10.21105/joss.08782) • ![MCP Server](https://img.shields.io/badge/MCP_Server-enabled-brightgreen) • ![MCP Tools](https://img.shields.io/badge/MCP_Tools-26-blue) • [![PyPI Downloads](https://static.pepy.tech/personalized-badge/nrel-erad?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/nrel-erad)

<p align="center"> 
<img src="docs/_static/light.png" width="400" style="display:flex;justify-content:center;">
</p>

# ERAD (<u>E</u>nergy <u>R</u>esilience <u>A</u>nalysis for electric <u>D</u>istribution systems)

[Visit full documentation here.](https://nlr-distribution-suite.github.io/erad/)

Understanding the impact of disaster events on people's ability to access critical services is key to designing appropriate programs to minimize the overall impact. Flooded roads, downed power lines, flooded power substation etc. could impact access to critical services like electricity, food, health and more. The field of disaster modeling is still evolving and so is our understanding of how these events would impact our critical infrastructures such power grid, hospitals, groceries, banks etc.

ERAD is a free, open-source Python toolkit for computing energy resilience measures in the face of hazards like earthquakes and flooding. It uses graph database to store data and perform computation at the household level for a variety of critical services that are connected by power distribution network. It uses asset fragility curves, which are functions that relate hazard severity to survival probability for power system assets including cables, transformers, substations, roof-mounted solar panels, etc. recommended in top literature. Programs like undergrounding, microgrid, and electricity backup units for critical infrastructures may all be evaluated using metrics and compared across different neighborhoods to assess their effects on energy resilience.

ERAD is designed to be used by researchers, students, community stakeholders, distribution utilities to understand and possibly evaluate effectiveness of different post disaster programs to improve energy resilience. It was funded by National Laboratory of the Rockies (NLR) and made publicly available with open license.



