from math import cos,\
                 degrees,\
                 pi,\
                 radians,\
                 sin
import matplotlib.pyplot as plt
from matplotlib.mlab import griddata

import numpy as np
from numpy import linspace,\
                  meshgrid,\
                  ndarray,\
                  zeros
#from seispy.geometry import deg2rad,\
from geometry import EARTH_RADIUS,\
                            geo2sph,\
                            sph2xyz,\
                            Vector
import geometry as geom

class VelocityModel(object):
    """
    This class is intended to facilitate querying and plotting of velocity models.

    For now, assume a model defined on a regular grid in spherical coordinates.

    .. todo::
       document this class.
    """
    def __init__(self, infile, fmt='fang'):
        if fmt.upper() == 'FANG':
            self._read_fang(infile)

    def _read_fang(self, infile):
        infile = open(infile)
        lon_nodes = [float(lon) for lon in infile.readline().split()]
        for i in range(len(lon_nodes)):
            if lon_nodes[i] < -180.:
                lon_nodes[i] += 360.
            elif lon_nodes[i] > 360.:
                lon_nodes[i] -= 360.
        lat_nodes = [float(lat) for lat in infile.readline().split()]
        z_nodes = [float(z) for z in infile.readline().split()]
        r_nodes = [EARTH_RADIUS - z for z in z_nodes]
        theta_nodes = [radians(90. - lat) for lat in lat_nodes]
        phi_nodes = [radians(lon) for lon in lon_nodes]
        self.model = {
            'Vp': zeros((len(r_nodes), len(theta_nodes), len(phi_nodes))),
            'Vs': zeros((len(r_nodes), len(theta_nodes), len(phi_nodes)))
            }
        self.nodes = zeros((len(r_nodes), len(theta_nodes), len(phi_nodes)),
                           dtype='float32, float32, float32')
        #initalize the grid of node coordinates
        for ir in range(len(r_nodes)):
            for itheta in range(len(theta_nodes)):
                for iphi in range(len(phi_nodes)):
                    self.nodes[ir, itheta, iphi] = (r_nodes[ir],
                                                    theta_nodes[itheta],
                                                    phi_nodes[iphi])
        self.r_max = max([n[0] for n in self.nodes[:, 0, 0]])
        self.r_min = min([n[0] for n in self.nodes[:, 0, 0]])
        self.r_mid = (self.r_max + self.r_min) / 2.
        self.dr = (self.r_max - self.r_min) / len(r_nodes)
        self.theta_max = max([n[1] for n in self.nodes[0, :, 0]])
        self.theta_min = min([n[1] for n in self.nodes[0, :, 0]])
        self.theta_mid = (self.theta_max + self.theta_min) / 2.
        self.dtheta = (self.theta_max - self.theta_min) / len(theta_nodes)
        self.phi_max = max([n[2] for n in self.nodes[0, 0, :]])
        self.phi_min = min([n[2] for n in self.nodes[0, 0, :]])
        self.phi_mid = (self.phi_max + self.phi_min) / 2.
        self.dphi = (self.phi_max - self.phi_min) / len(phi_nodes)
        #initialize the grids of velocity values
        for phase in ('Vp', 'Vs'):
            for ir in range(len(r_nodes)):
                for itheta in range(len(theta_nodes)):
                    line = infile.readline().split()
                    for iphi in range(len(line)):
                        self.model[phase][ir, itheta, iphi] = float(line[iphi])

    def _get_V(self, r, theta, phi, phase):
        if phi < 0:
            phi += 2 * pi
        if r > self.nodes[0, 0, 0][0]\
                or r < self.nodes[-1, 0, 0][0]\
                or theta > self.nodes [0, 0, 0][1]\
                or theta < self.nodes[0, -1, 0][1]\
                or phi < self.nodes[0, 0, 0][2]\
                or phi > self.nodes[0, 0, -1][2]:
            raise ValueError("point lies outside velocity model")
        ir0, itheta0, iphi0 = None, None, None
        for ir in range(self.nodes.shape[0] - 1):
            if self.nodes[ir, 0, 0][0] > r > self.nodes[ir + 1, 0, 0][0]:
                ir0 = ir
                break
        for itheta in range(self.nodes.shape[1] - 1):
            if self.nodes[0, itheta, 0][1] > theta > self.nodes[0, itheta + 1, 0][1]:
                itheta0 = itheta
                break
        for iphi in range(self.nodes.shape[2] - 1):
            if self.nodes[0, 0, iphi][2] < phi < self.nodes[0, 0, iphi + 1][2]:
                iphi0 = iphi
                break
        if ir0 == None:
            ir0 = [n[0] for n in self.nodes[:, 0, 0]].index(r)
        if itheta0 == None:
            itheta0 = [n[1] for n in self.nodes[0, :, 0]].index(theta)
        if iphi0 == None:
            iphi0 = [n[2] for n in self.nodes[0, 0, :]].index(phi)
        #still need to deal with edges properly
        #do a trilinear interpolation
        model = self.model[phase]
        V000 = model[ir0, itheta0, iphi0]
        V100 = model[ir0 + 1, itheta0, iphi0]
        V010 = model[ir0, itheta0 + 1, iphi0]
        V110 = model[ir0 + 1, itheta0 + 1, iphi0]
        V001 = model[ir0, itheta0, iphi0 + 1]
        V101 = model[ir0 + 1, itheta0, iphi0 + 1]
        V011 = model[ir0, itheta0 + 1, iphi0 + 1]
        V111 = model[ir0 + 1, itheta0 + 1, iphi0 + 1]
        dV00 = V100 - V000
        dV10 = V110 - V010
        dV01 = V101 - V001
        dV11 = V111 - V011
        dr = self.nodes[ir0 + 1, 0, 0][0] - self.nodes[ir0, 0, 0][0]
        delta_r = r - self.nodes[ir0, 0, 0][0]
        V00 = V000 + (dV00 / dr) * delta_r
        V10 = V010 + (dV10 / dr) * delta_r
        V01 = V001 + (dV01 / dr) * delta_r
        V11 = V011 + (dV11 / dr) * delta_r
        dV0 = V10 - V00
        dV1 = V11 - V01
        dtheta = self.nodes[0, itheta + 1, 0][1] - self.nodes[0, itheta, 0][1]
        delta_theta = theta - self.nodes[0, itheta, 0][1]
        V0 = V00 + (dV0 / dtheta) * delta_theta
        V1 = V01 + (dV1 / dtheta) * delta_theta
        dV = V1 - V0
        dphi = self.nodes[0, 0, iphi + 1][2] - self.nodes[0, 0, iphi][2]
        delta_phi = phi - self.nodes[0, 0, iphi][2]
        V = V0 + (dV / dphi) * delta_phi
        return V

    def get_Vp(self, lat, lon, depth):
        r, theta, phi = geo2sph(lat, lon, depth)
        return self._get_V(r, theta, phi, 'Vp')

    def get_Vs(self):
        r, theta, phi = geo2sph(lat, lon, depth)
        return self._get_V(r, theta, phi, 'Vs')

    def _plot(self, lat, lon, depth, phase):
        NPTS = 50
        X, Y, V = [], [], []
        if lat == -999 and lon == -999:
            title = "Depth horizon - %.1f [km]" % depth
            xlabel = "Distance from %.2f [km]" % self.phi_mid
            ylabel = "Distance from %.2f [km]" % self.theta_mid
            r = EARTH_RADIUS - depth
            theta_nodes = linspace(self.theta_min + 0.01 * self.dtheta,
                                   self.theta_max - 0.01 * self.dtheta,
                                   NPTS)
            phi_nodes = linspace(self.phi_min + 0.01 * self.dphi,
                                   self.phi_max - 0.01 * self.dphi,
                                   NPTS)
            X, Y = meshgrid(phi_nodes, theta_nodes)
            V = np.ndarray(shape=X.shape)
            for i in range(X.shape[0]):
                for j in range(X.shape[1]):
                    V[i, j] = self._get_V(r, Y[i, j], X[i, j], phase)
                    X[i, j] = r * sin(self.phi_mid) - r * sin(X[i, j])
                    Y[i, j] = r * sin(pi / 2 - Y[i, j]) - r * sin(pi / 2 - self.theta_mid)
        elif lat == -999 and depth == -999:
            title = "Vertical, longitudinal slice - %.2f" % lon
            xlabel = "Distance from %.2f [km]" % (90 - degrees(self.theta_mid))
            ylabel = "Depth from surface [km]"
            phi = radians(lon)
            r_nodes = linspace(self.r_min + 0.01 * self.dr,
                               self.r_max - 0.01 * self.dr,
                               NPTS)
            theta_nodes = linspace(self.theta_min + 0.01 * self.dtheta,
                                   self.theta_max - 0.01 * self.dtheta,
                                   NPTS)
            X, Y = meshgrid(theta_nodes, r_nodes)
            V = np.ndarray(shape=X.shape)
            for i in range(X.shape[0]):
                for j in range(X.shape[1]):
                    r = Y[i, j]
                    theta = X[i, j]
                    V[i, j] = self._get_V(r, theta, phi, phase)
                    X[i, j] = r * sin(theta - self.theta_mid)
                    Y[i, j] = r * cos(theta - self.theta_mid) - self.r_max
        elif lon == -999 and depth == -999:
            title = "Vertical, latitudinal slice - %.2f" % lat
            xlabel = "Distance from %.2f [km]" % degrees(self.phi_mid)
            ylabel = "Depth from surface [km]"
            #get data points
            theta = radians(90 - lat)
            r_nodes = linspace(self.r_min + 0.01 * self.dr,
                               self.r_max - 0.01 * self.dr,
                               NPTS)
            phi_nodes = linspace(self.phi_min + 0.01 * self.dphi,
                                 self.phi_max - 0.01 * self.dphi,
                                 NPTS)
            X, Y = meshgrid(phi_nodes, r_nodes)
            V = np.ndarray(shape=X.shape)
            for i in range(X.shape[0]):
                for j in range(X.shape[1]):
                    V[i, j] = self._get_V(Y[i, j], theta, X[i, j], phase)
                    phi, r = X[i, j], Y[i, j]
                    X[i, j] = r * cos(pi / 2 - (phi - self.phi_mid))
                    Y[i, j] = r * sin(pi / 2 - (phi - self.phi_mid)) - self.r_max
        fig = plt.figure()
        fig.suptitle(title)
        ax = fig.add_subplot(1, 1, 1)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        im = ax.pcolormesh(X, Y, V,
                           #vmin=4.0,
                           #vmax=8.5,
                           cmap=plt.get_cmap('hsv'))
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("%s [km/s]" % phase)
        plt.show()
        

    def plot_Vp(self, lat=-999, lon=-999, depth=-999):
        self._plot(lat, lon, depth, 'Vp')

    def plot_Vs(self, lat=-999, lon=-999, depth=-999):
        self._plot(lat, lon, depth, 'Vs')

    def plot_VpVs_ratio(self):
        pass