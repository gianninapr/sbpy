Bibliography Tracking Module (`sbpy.bib`)
=========================================

Introduction
------------

`sbpy` classes and functions can automatically report citations to the
user through a bibliography registry. The idea behind this service is
to make it easier to properly acknowledge and reference those who
designed methods and tools used.

ADS Query Requirements for the `sbpy.bib` Module
------------------------------------------------

In order to use the `~sbpy.bib` functionality and obtain author names
from the bibcode provided by the user, the user has to have the `~ads`
module installed. More information on this module is found in the `ads
Docs <https://ads.readthedocs.io/en/latest/>`_. In order for the
`~ads` queries, essential to `~sbpy.bib`, to work the user has to have
the module installed, and their own personal developer key.  As stated
in the documentation:

1. You'll need an API key from NASA ADS labs. Get `an ADS account
<https://ui.adsabs.harvard.edu/user/account/register>`_, visit account
settings and generate a new API token.

2. When you get your API key, save it to a file called ``~/.ads/dev_key`` or
save it as an environment variable named ``ADS_DEV_KEY``

3. Install the `ads` python module, e.g., if using pip: ``pip install ads``

How to use `~sbpy.bib`
----------------------

Use `~sbpy.bib.track()` to enable citation tracking. Every method
called after activating the tracking will register any relevant
citations. Each citation is associated with a tag that enables the
user to identify which aspect of the method the citation is relevant
to:

    >>> from sbpy import bib, data
    >>> bib.track()
    >>> eph = data.Ephem.from_horizons('433')    # doctest: +SKIP
    >>> print(bib.to_text())                     # doctest: +SKIP
    sbpy.data.Ephem.from_horizons:
      data service:
          Giorgini, Yeomans, Chamberlin et al. 1996, AAS/Division for Planetary Sciences Meeting Abstracts #28, 25.04

In this case, ``Giorgini et al. 1996, 1996DPS....28.2504G`` is
relevant to the implementation of the JPL Horizons system that is
queried by the `~sbpy.data.Ephem.from_horizons`
function. `~sbpy.bib.to_text` outputs the current citation registry in
simple text form.

To disable tracking, use `~sbpy.bib.stop()`:

    >>> bib.stop()

To clear any previous citations:

    >>> bib.reset()

Bibliography tracking can also be used in a context manager:

    >>> from sbpy import bib, data
    >>> with bib.Tracking(bib.to_text):
    ...     eph = data.Ephem.from_horizons('Ceres') # doctest: +SKIP
    sbpy.data.Ephem.from_horizons:
      data service:
          Giorgini, Yeomans, Chamberlin et al. 1996, AAS/Division for Planetary Sciences Meeting Abstracts #28, 25.04

Automatic reporting
-------------------

If tracking is enabled when Python exits, the bibliography will be automatically reported.  ``ipython`` users can enable tracking at startup so that no citations are left behind.  For example, add the following to a startup script, such as ``~/.ipython/profile_default/startup/99-user.py``:

.. code-block:: python

    import sbpy.bib
    sbpy.bib.track()


Output formats
--------------

Bibliographies can be generated in different output formats:

Unformatted (`~sbpy.bib.show`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.show() # doctest: +SKIP
    sbpy.data.Ephem.from_horizons:
      data service:
        1996DPS....28.2504G


Simple text (`~sbpy.bib.to_text`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.to_text() # doctest: +SKIP
    sbpy.data.Ephem.from_horizons:
      data service:
          Giorgini, Yeomans, Chamberlin et al. 1996, AAS/Division for Planetary Sciences Meeting Abstracts #28, 25.04


BibTeX (`~sbpy.bib.to_bibtex`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.to_bibtex() # doctest: +SKIP
    % sbpy.data.Ephem.from_horizons/data service:
    @INPROCEEDINGS{1996DPS....28.2504G,
           author = {{Giorgini}, J.~D. and {Yeomans}, D.~K. and {Chamberlin}, A.~B. and
            {Chodas}, P.~W. and {Jacobson}, R.~A. and {Keesey}, M.~S. and
            {Lieske}, J.~H. and {Ostro}, S.~J. and {Standish}, E.~M. and
            {Wimberly}, R.~N.},
            title = "{JPL's On-Line Solar System Data Service}",
        booktitle = {AAS/Division for Planetary Sciences Meeting Abstracts \#28},
             year = 1996,
            month = Sep,
              eid = {25.04},
            pages = {25.04},
           adsurl = {https://ui.adsabs.harvard.edu/#abs/1996DPS....28.2504G},
          adsnote = {Provided by the SAO/NASA Astrophysics Data System}
    }

AASTeX (`~sbpy.bib.to_aastex`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.to_aastex() # doctest: +SKIP
    % sbpy.data.Ephem.from_horizons/data service:
    \bibitem[Giorgini et al.(1996)]{1996DPS....28.2504G} Giorgini, J.~D.,
    Yeomans, D.~K., Chamberlin, A.~B., et al.\ 1996, AAS/Division for
    Planetary Sciences Meeting Abstracts \#28 , 25.04.

Icarus (`~sbpy.bib.to_icarus`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.to_icarus() # doctest: +SKIP
    % sbpy.data.Ephem.from_horizons/data service:
    \bibitem[Giorgini et al.(1996)]{1996DPS....28.2504G} Giorgini, J.~D.,
    and 9 colleagues 1996.\ JPL's On-Line Solar System Data Service.\
    AAS/Division for Planetary Sciences Meeting Abstracts \#28 25.04.

MNRAS (`~sbpy.bib.to_mnras`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    >>> bib.to_mnras() # doctest: +SKIP
    % sbpy.data.Ephem.from_horizons/data service:
    \bibitem[\protect\citeauthoryear{Giorgini, et al.}{1996}]{1996DPS....28.2504G}
    Giorgini J.~D., et al., 1996, AAS/Division for Planetary Sciences
    Meeting Abstracts \#28, 25.04
    
    
Please note that the NASA ADS API is still experimental and suffers
from hickups. Queries might fail, leading to warnings. If you perform
a query, please check if there are any warning messages included. If
so, please re-try the query until it is successful.

Other bibliography styles, for instance in accordance to specific
journal rules, can be readily implemented.


Reference/API
-------------
.. automodapi:: sbpy.bib
    :no-heading:
