# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
======================
sbpy data.Orbit Module
======================

Class for querying, manipulating, integrating, and fitting orbital elements.

created on June 04, 2017
"""
import os
from numpy import array, ndarray, double, arange, rad2deg
from astropy.time import Time
from astropy.table import vstack, Column
from astroquery.jplhorizons import Horizons
import astropy.units as u

from .. import bib
from . import conf, DataClass

__all__ = ['Orbit']


class Orbit(DataClass):
    """Class for querying, manipulating, integrating, and fitting orbital
    elements"""

    @classmethod
    def from_horizons(cls, targetids, id_type='smallbody',
                      epochs=None, center='500@10',
                      **kwargs):
        """Load target orbital elements from
        `JPL Horizons <https://ssd.jpl.nasa.gov/horizons.cgi>`_ using
        `astroquery.jplhorizons.HorizonsClass.elements`

        Parameters
        ----------
        targetids : str or iterable of str
            Target identifier, i.e., a number, name, designation, or JPL
            Horizons record number, for one or more targets.
        id_type : str, optional
            The nature of ``targetids`` provided; possible values are
            ``'smallbody'`` (asteroid or comet), ``'majorbody'`` (planet or
            satellite), ``'designation'`` (asteroid or comet designation),
            ``'name'`` (asteroid or comet name), ``'asteroid_name'``,
            ``'comet_name'``, ``'id'`` (Horizons id).
            Default: ``'smallbody'``
        epochs : `~astropy.time.Time` object or iterable thereof, or dict, optional
            Epochs of elements to be queried; a list, tuple or
            `~numpy.ndarray` of `~astropy.time.Time` objects or Julian
            Dates as floats should be used for a number of discrete
            epochs; a dictionary including keywords ``start``,
            ``step``, and ``stop`` can be used to generate a range of
            epochs (see
            `~astroquery.jplhorizons.HorizonsClass.Horizons.elements`
            for details); if ``None`` is provided, current date and
            time are used. Default: ``None``
        center : str, optional, default ``'500@10'`` (center of the Sun)
            Elements will be provided relative to this position.
        **kwargs : optional
            Arguments that will be provided to
            `astroquery.jplhorizons.HorizonsClass.elements`.

        Notes
        -----
        * For detailed explanations of the queried fields, refer to
          `astroquery.jplhorizons.HorizonsClass.elements` and the
          `JPL Horizons documentation <https://ssd.jpl.nasa.gov/?horizons_doc>`_.
        * By default, elements are provided in the J2000.0 reference
          system and relative to the ecliptic and mean equinox of the
          reference epoch. Different settings can be chosen using
          additional keyword arguments as used by
          `astroquery.jplhorizons.HorizonsClass.elements`.

        Returns
        -------
        `~Orbit` object

        Examples
        --------
        >>> from sbpy.data import Orbit
        >>> from astropy.time import Time
        >>> epoch = Time('2018-05-14', scale='utc')
        >>> eph = Orbit.from_horizons('Ceres', epochs=epoch)
        ... # doctest: +REMOTE_DATA
        """

        # modify epoch input to make it work with astroquery.jplhorizons
        # maybe this stuff should really go into that module....
        if epochs is None:
            epochs = [Time.now().jd]
        elif isinstance(epochs, Time):
            epochs = [Time(epochs).jd]
        elif isinstance(epochs, dict):
            for key, val in epochs.items():
                if isinstance(val, Time):
                    val.format = 'iso'
                    val.out_subfmt = 'date_hm'
                    epochs[key] = "'"+val.value+"'"
                else:
                    epochs[key] = "'"+epochs[key]+"'"
        elif isinstance(epochs, (list, tuple, ndarray)):
            new_epochs = [None] * len(epochs)
            for i in range(len(epochs)):
                if isinstance(epochs[i], Time):
                    new_epochs[i] = epochs[i].jd
                else:
                    new_epochs[i] = epochs[i]
            epochs = new_epochs

        # if targetids is a list, run separate Horizons queries and append
        if not isinstance(targetids, (list, ndarray, tuple)):
            targetids = [targetids]

        # append elements table for each targetid
        all_elem = None
        for targetid in targetids:

            # load elements using astroquery.jplhorizons
            obj = Horizons(id=targetid, id_type=id_type,
                           location=center, epochs=epochs)

            elem = obj.elements(**kwargs)

            # workaround for current version of astroquery to make
            # column units compatible with astropy.table.QTable
            # should really change '---' units to None in
            # astroquery.jplhorizons.__init__.py
            for column_name in elem.columns:
                if elem[column_name].unit == '---':
                    elem[column_name].unit = None

            if all_elem is None:
                all_elem = elem
            else:
                all_elem = vstack([all_elem, elem])

        # identify time scales returned by Horizons query
        timescales = ['TDB'] * len(all_elem)
        all_elem['timescale'] = timescales

        if bib.status() is None or bib.status():
            bib.register('sbpy.data.Orbit.from_horizons',
                         {'data service': '1996DPS....28.2504G'})

        return cls.from_table(all_elem)

    # functions using pyoorb

    def _to_oo(self, timescale=None):
        """Converts this orbit object to a openorb-compatible orbit array

        Parameters
        ----------
        timescale : str (``UTC``|``UT1``|``TT``|``TAI``)
            overrides timescale provided in `~Orbit` object; Default:
            ``None``.

        Notes
        -----
        * If no ``timescale`` field is provided in the orbit table and the
          ``timescale`` option is not used (None), ``timescale=UTC`` is
          assumed.
        * ``TDB`` times are currently used as ``TT`` times, introducing
          uncertainties of less than 0.002 seconds in the timing.

        """

        # identify orbit type based on available table columns
        if 'orbtype' in self.field_names:
            orbittype = self.table['orbtype'][0]
        else:
            orbittype = None

            for testtype in ['KEP', 'COM', 'CART']:
                try:
                    for field in conf.oorb_orbit_fields[testtype][1:6]:
                        self.__getitem__(field)
                    orbittype = testtype
                    break
                except KeyError:
                    pass

        if orbittype is None:
            raise ValueError(
                'orbit type cannot be determined from elements')

        # rename TDB to TT, if ``timescale`` fields available
        if ('timescale' in self.field_names and
                any(self.table['timescale'] == 'TDB')):
            self.table['timescale'][self.table['timescale'] == 'TDB'] = 'TT'
        if timescale == 'TDB':
            timescale = 'TT'

        if timescale is not None:
            # override timescale, if provided
            timescale_ = [conf.oorb_timeScales[timescale]] * len(self.table)
        elif 'timescale' not in self.field_names:
            # assume UTC if no timescale information provided
            timescale_ = [conf.oorb_timeScales['UTC']] * len(self.table)
        else:
            # use ``timescale`` field information
            timescale_ = [conf.oorb_timeScales[t]
                          for t in self.table['timescale']]

        # implant ``targetname`` field information, if not available
        if 'targetname' not in self.field_names:
            self.table['targetname'] = ['orbit_'+str(i) for i in
                                        range(len(self.table))]

        # assemble orbit array for oorb_ephemeris
        if orbittype == 'COM':
            # cometary orbit: id q e i node argperi t_p otype epoch t H G
            orbits = array(array([arange(0, len(self.table), 1),
                                  self['q'].to('au').value,
                                  self['e'].data,
                                  self['i'].to('radian').value,
                                  self['Omega'].to('radian').value,
                                  self['w'].to('radian').value,
                                  (self['Tp_jd'].to('d').value -
                                   2400000.5),
                                  [conf.oorb_elemType[orbittype]] *
                                  len(self.table),
                                  (self['epoch'].to('d').value
                                   - 2400000.5),
                                  timescale_,
                                  self['H'].value,
                                  self['G'].data]).transpose(),
                           dtype=double, order='F')
        elif orbittype == 'KEP':
            # keplerian orbit: id a e i node argperi M otype epoch ttype H G
            orbits = array(array([arange(0, len(self.table), 1),
                                  self['a'].to('au').value,
                                  self['e'].data,
                                  self['incl'].to('radian').value,
                                  self['Omega'].to('radian').value,
                                  self['w'].to('radian').value,
                                  self['M'].to('radian').value,
                                  [conf.oorb_elemType[orbittype]] *
                                  len(self.table),
                                  (self['epoch'].to('d').value
                                   - 2400000.5),
                                  timescale_,
                                  self['H'].value,
                                  self['G'].data]).transpose(),
                           dtype=double, order='F')
        elif orbittype == 'CART':
            # cartesian orbit: id x y z dx dy dz otype epoch ttype H G
            orbits = array(array([arange(0, len(self.table), 1),
                                  self['x'].to('au').value,
                                  self['y'].to('au').value,
                                  self['z'].to('au').value,
                                  self['dx'].to('au/d').value,
                                  self['dy'].to('au/d').value,
                                  self['dz'].to('au/d').value,
                                  [conf.oorb_elemType[orbittype]] *
                                  len(self.table),
                                  self['datetime_jd'].to('d').value
                                  - 2400000.5,
                                  timescale_,
                                  self['H'].data,
                                  self['G'].data]).transpose(),
                           dtype=double, order='F')

        return orbits

    def oo_transform(self, orbittype, timescale=None, ephfile='de430'):
        """Uses pyoorb to transform this orbit object to a different
        orbit type definition. Required fields are:

        * target identifier (``'targetname'``)
        * semi-major axis (``'a'``, for Keplerian orbit) or perihelion
          distance (``'q'``, for cometary orbit), typically in au or
          or x-component of state vector (``'x'``, for cartesian orbit),
          typically in au
        * eccentricity (``'e'``, for Keplerian or cometary orbit) or
          y-component of state vector (``'y'``, for cartesian orbit) in
          au
        * inclination (``'i'``, for Keplerian or cometary orbit) in
          degrees or z-component of state vector (``'z'``, for cartesian
          orbit) in au
        * longitude of the ascending node (``'Omega'``, for Keplerian or
          cometary orbit) in degrees or x-component of velocity vector
          (``'vx'``, for cartesian orbit), au/day
        * argument of the periapsis (``'w'``, for Keplerian or cometary
          orbit) in degrees or y-component of velocity vector (``'vy'``,
          for cartesian orbit) in au/day
        * mean anomaly (``'M'``, for Keplerian orbits) in degrees or
          perihelion epoch (``'Tp_jd'``, for cometary orbits) in JD or
          z-component of velocity vector (``'vz'``, for cartesian orbit)
          in au/day
        * epoch (``'epoch'``) in JD
        * epoch time scale (``'epoch_scale'``) either one of:
          ``'UTC'`` | ``'UT1'`` | ``'TT'`` | ``'TAI'``
        * absolute magnitude (``'H'``) in mag
        * photometric phase slope (``'G'``)

        Parameters
        ----------
        orbittype : str
            Orbit definition to be transformed to; available orbit
            definitions are ``KEP`` (Keplerian elements), ``CART``
            (cartesian elements), ``COM`` (cometary elements).
        timescale : str
            Overrides time scale to be used in the transformation;
            the following
            values are allowed: ``'UTC'``, ``'UT1'``, ``'TT'``,
            ``'TAI'``. If ``None`` is used, the same time scale as in the
            existing orbit is used. Default: ``None``
        ephfile : str, optional
            Planet and Lunar ephemeris file version as provided by JPL
            to be used in the propagation. Default: ``'de430'``

        Returns
        -------
        `~Orbit` object

        Examples
        --------
        Obtain the current state vector (cartesian definition, ``CART``) for
        asteroid Ceres.

        >>> from sbpy.data import Orbit
        >>> ceres = Orbit.from_horizons('Ceres')  # doctest: +REMOTE_DATA
        >>> statevec = ceres.oo_transform('CART') # doctest: +SKIP
        >>> print(statevec)  # doctest: +SKIP
        <QTable length=1>
           id           x                   y          ...    H       G    timescale
                        AU                  AU         ...   mag
          str7       float64             float64       ... float64 float64    str2
        ------- ------------------ ------------------- ... ------- ------- ---------
        1 Ceres -1.967176101061908 -1.7891189971612211 ...    3.34    0.12        TT
        """
        import pyoorb

        # initialize pyoorb
        if os.getenv('OORB_DATA') is None:
            # oorb installed using conda
            pyoorb.pyoorb.oorb_init()
        else:
            ephfile = os.path.join(os.getenv('OORB_DATA'), ephfile+'.dat')
            pyoorb.pyoorb.oorb_init(ephfile)

        if timescale is None:
            timescale = self.table['timescale'][0]

        # derive and apply default units
        default_units = {}
        for idx, field in enumerate(conf.oorb_orbit_fields[orbittype]):
            try:
                default_units[self._translate_columns(
                    field)[0]] = conf.oorb_orbit_units[orbittype][idx]
            except KeyError:
                pass
        for colname in self.field_names:
            if (colname in default_units.keys() and
                not isinstance(self[colname],
                               (u.Quantity, u.CompositeUnit))):
                self[colname].unit = default_units[colname]

        oo_orbits, err = pyoorb.pyoorb.oorb_element_transformation(
            in_orbits=self._to_oo(timescale),
            in_element_type={'CART': 1, 'COM': 2, 'KEP': 3,
                             'DEL': 4, 'EQX': 5}[orbittype])

        if err != 0:
            RuntimeError('pyoorb failed with error code {:d}'.format(err))

        # reorder data in Orbit object
        field_names = conf.oorb_orbit_fields[orbittype]

        columns = []
        for i, col in enumerate(oo_orbits.transpose()):
            columns.append(Orbit._unit_apply(
                col, conf.oorb_orbit_units[orbittype][i]))
        orbits = self.from_columns(columns, names=field_names)

        for i, col in enumerate(orbits.field_names):
            # convert from radians to degrees where unit == deg
            if conf.oorb_orbit_units[orbittype][i] == 'deg':
                orbits._table[col] = rad2deg(orbits[col])

        # replace id column with actual target names from original orbits
        orbits.table.replace_column('id', self['targetname'])

        # replace orbtype and epoch_scale columns
        orbits.table.replace_column('orbtype',
                                    [orbittype] * len(orbits.table))
        orbits.table.replace_column('epoch_scale',
                                    [timescale] * len(orbits.table))

        # identify time scales returned by Horizons query
        timescales = [timescale] * len(orbits.table)
        orbits.table['timescale'] = timescales

        if bib.status() is None or bib.status():
            bib.register('sbpy.data.Ephem.from_oo',
                         {'method': '2009M&PS...44.1853G',
                          'implementation': 'https://github.com/oorb/oorb'})

        return orbits

    def oo_propagate(self, epoch, timescale='UTC',
                     dynmodel='N', ephfile='de430'):
        """Uses pyoorb to propagate this `~Orbit` object. Required fields are:

        * target identifier (``'targetname'``)
        * semi-major axis (``'a'``, for Keplerian orbit) or perihelion
          distance (``'q'``, for cometary orbit), typically in au or
          or x-component of state vector (``'x'``, for cartesian orbit),
          typically in au
        * eccentricity (``'e'``, for Keplerian or cometary orbit) or
          y-component of state vector (``'y'``, for cartesian orbit) in
          au
        * inclination (``'i'``, for Keplerian or cometary orbit) in
          degrees or z-component of state vector (``'z'``, for cartesian
          orbit) in au
        * longitude of the ascending node (``'Omega'``, for Keplerian or
          cometary orbit) in degrees or x-component of velocity vector
          (``'vx'``, for cartesian orbit), au/day
        * argument of the periapsis (``'w'``, for Keplerian or cometary
          orbit) in degrees or y-component of velocity vector (``'vy'``,
          for cartesian orbit) in au/day
        * mean anomaly (``'M'``, for Keplerian orbits) in degrees or
          perihelion epoch (``'Tp_jd'``, for cometary orbits) in JD or
          z-component of velocity vector (``'vz'``, for cartesian orbit)
          in au/day
        * epoch (``'epoch'``) in JD
        * epoch time scale (``'epoch_scale'``) either one of:
          ``'UTC'`` | ``'UT1'`` | ``'TT'`` | ``'TAI'``
        * absolute magnitude (``'H'``) in mag
        * photometric phase slope (``'G'``)

        Parameters
        ----------
        epoch : `~astropy.time.Time` object or float
            Epoch to which the orbit will be propagated to. A float
            value will be interpreted as Julian date.
        timescale : str, optional
            Timescale to be used in the propagation; the following
            values are allowed: ``'UTC'``, ``'UT1'``, ``'TT'``,
            ``'TAI'``. Default: ``'UTC'``
        dynmodel : str, optional
            The dynamical model to be used in the propagation: ``'N'``
            for n-body simulation or ``'2'`` for a 2-body
            simulation. Default: ``'N'``
        ephfile : str, optional
            Planet and Lunar ephemeris file version as provided by JPL
            to be used in the propagation. Default: ``'de430'``

        Returns
        -------
        `~Orbit` object

        Examples
        --------
        Propagate the orbit of Ceres 100 days into the future:

        >>> from sbpy.data import Orbit
        >>> from astropy.time import Time
        >>> epoch = Time.now().jd + 100
        >>> ceres = Orbit.from_horizons('Ceres')      # doctest: +REMOTE_DATA
        >>> future_ceres = ceres.oo_propagate(epoch)  # doctest: +SKIP
        >>> print(future_ceres)  # doctest: +SKIP
        <QTable length=1>
           id           a                  e          ...    H       G    timescale
                        AU                            ...   mag
          str7       float64            float64       ... float64 float64    str3
        ------- ----------------- ------------------- ... ------- ------- ---------
        1 Ceres 2.769331727251861 0.07605371361208543 ...    3.34    0.12       UTC        """

        import pyoorb

        # initialize pyoorb
        if os.getenv('OORB_DATA') is None:
            # oorb installed using conda
            pyoorb.pyoorb.oorb_init()
        else:
            ephfile = os.path.join(os.getenv('OORB_DATA'), ephfile+'.dat')
            pyoorb.pyoorb.oorb_init(ephfile)

        # identify orbit type based on available table columns
        orbittype = None
        for testtype in ['KEP', 'COM', 'CART']:
            try:
                self._translate_columns(
                    conf.oorb_orbit_fields[testtype][1:6])
                orbittype = testtype
                break
            except KeyError:
                pass

        if orbittype is None:
            raise ValueError(
                'orbit type cannot be determined from elements')

        # derive and apply default units
        default_units = {}
        for idx, field in enumerate(conf.oorb_orbit_fields[orbittype]):
            try:
                default_units[self._translate_columns(
                    field)[0]] = conf.oorb_orbit_units[orbittype][idx]
            except KeyError:
                pass
        for colname in self.field_names:
            if (colname in default_units.keys() and
                not isinstance(self[colname],
                               (u.Quantity, u.CompositeUnit))):
                self[colname].unit = default_units[colname]

        if isinstance(epoch, Time):
            ooepoch = [epoch.jd-2400000.5, conf.oorb_timeScales[timescale]]
        else:
            ooepoch = [epoch-2400000.5, conf.oorb_timeScales[timescale]]

        oo_orbits, err = pyoorb.pyoorb.oorb_propagation(
            in_orbits=self._to_oo(),
            in_epoch=ooepoch,
            in_dynmodel=dynmodel)

        if err != 0:
            RuntimeError('pyoorb failed with error code {:d}'.format(err))

        # reorder data in Orbit object
        field_names = conf.oorb_orbit_fields[orbittype]

        columns = []
        for i, col in enumerate(oo_orbits.transpose()):
            columns.append(Orbit._unit_apply(
                col, conf.oorb_orbit_units[orbittype][i]))
        orbits = self.from_columns(columns, names=field_names)

        for i, col in enumerate(orbits.field_names):
            # convert from radians to degrees where unit == deg
            if conf.oorb_orbit_units[orbittype][i] == 'deg':
                orbits._table[col] = rad2deg(orbits[col])

        # replace id column with actual target names from original orbits
        orbits.table.replace_column('id', self.table['targetname'])

        # replace orbtype and epoch_scale columns
        orbits.table.replace_column('orbtype',
                                    [orbittype] * len(orbits.table))
        orbits.table.replace_column('epoch_scale',
                                    [timescale] * len(orbits.table))

        # adjust epochs to standard jd
        orbits.table['epoch'] = orbits.table['epoch'] + 2400000.5*u.d

        # identify time scales returned by Horizons query
        timescales = [timescale] * len(orbits.table)
        orbits.table['timescale'] = timescales

        if bib.status() is None or bib.status():
            bib.register('sbpy.data.Ephem.from_oo',
                         {'method': '2009M&PS...44.1853G',
                          'implementation': 'https://github.com/oorb/oorb'})

        return orbits
