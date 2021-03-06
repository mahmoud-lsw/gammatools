#!/usr/bin/env python

import matplotlib.pyplot as plt
import gammatools
from gammatools.dm.dmmodel import *
from gammatools.core.util import *
from gammatools.dm.jcalc import *
import sys
import yaml
import copy

import argparse

def make_halo_plots(halo_models,cat):

    fig0 = plt.figure()
    ax0 = fig0.add_subplot(111)

    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111)
    
    fig2 = plt.figure()
    ax2 = fig2.add_subplot(111)

    for h in halo_models:
        dp = DensityProfile.create(cat[h])
        jp = LoSIntegralFn.create(cat[h])

        prefix = h + '_'

        x = np.linspace(-1.0,2,100)


        ax0.plot(10**x,dp.rho(10**x*Units.kpc)/Units.gev_cm3,label=h)

        psi_edge = np.radians(10**np.linspace(np.log10(0.1),np.log10(45.),100))

        psi = 0.5*(psi_edge[1:] + psi_edge[:-1])

        jval = jp(psi)

        domega = 2*np.pi*(np.cos(psi_edge[1:]) - psi_edge[:-1])
        jcum = np.cumsum(domega*jval)

        ax1.plot(np.degrees(psi),jval/Units.gev2_cm5,label=h)
        ax2.plot(np.degrees(psi),jcum/Units.gev2_cm5,label=h)


        ax0.set_yscale('log')
        ax0.set_xscale('log')
        ax0.axvline(8.5,label='Solar Radius')
        ax0.grid(True)
        ax0.set_xlabel('Distance [kpc]')
        ax0.set_ylabel('DM Density [GeV cm$^{-3}$]')

        ax0.legend()

        fig0.savefig(prefix + 'density_profile.png')

    #psi = np.arctan(10**x*Units.kpc/(8.5*Units.kpc))

        ax1.set_yscale('log')
        ax1.set_xscale('log')
        ax1.grid(True)
        ax1.set_xlabel('Angle [deg]')
        ax1.set_ylabel('J Factor [GeV$^{-2}$ cm$^{-5}$ sr$^{-1}$]')

        ax1.legend()

        fig1.savefig(prefix + 'jval.png')

        ax2.set_yscale('log')
        ax2.set_xscale('log')
        ax2.grid(True)
        ax2.set_xlabel('GC Angle [deg]')
        ax2.set_ylabel('Cumulative J Factor [GeV$^{-2}$ cm$^{-5}$]')

        ax2.legend()

        fig2.savefig(prefix + 'jcum.png')

usage = "usage: %(prog)s [options]"
description = """Compute the annihilation flux and yield spectrum for a 
DM halo and WIMP model."""

parser = argparse.ArgumentParser(usage=usage,description=description)

parser.add_argument('--halo_model', default=None, required=True,
                    help = 'Set the name of the halo model.  This will be used '
                    'to look up the parameters for this halo from the halo '
                    'model file.')

parser.add_argument('--channel', default=None, required=True,
                    help = 'Set the DM annihilation/decay channel.')

parser.add_argument('--sigmav', default=3E-26, 
                    help = 'Set the annihilation cross section in cm^3 s^{-1}.')

parser.add_argument('--mass', default='1.0/4.0/25', 
                    help = 'Set the array of WIMP masses at which the DM flux '
                    'will be evaluation.')

args = parser.parse_args()

halo_model_lib = yaml.load(open(os.path.join(gammatools.PACKAGE_ROOT,
                                  'data/dm_halo_models.yaml'),'r'))

if not args.halo_model in halo_model_lib:

    print 'No such model file: ', args.halo_model

    for k in sorted(halo_model_lib.keys()): 
        print '%20s %s'%(k, halo_model_lib[k])
    sys.exit(1)

halo_model = halo_model_lib[args.halo_model]
massv = [float(t) for t in args.mass.split('/')]
massv = np.linspace(massv[0],massv[1],massv[2])
sigmav = args.sigmav*Units.cm3_s

flux_header = 'Column 0 Energy [Log10(E/MeV)]\n'
flux_header += 'Column 1 Halo Offset Angle [radians]\n'
flux_header += 'Column 2 E^2 dF/dE [MeV cm^{-2} s^{-1} sr^{-1}]\n'
flux_header += 'Column 3 dF/dE [MeV^{-1} cm^{-2} s^{-1} sr^{-1}]\n'

yield_header = 'Column 0 Energy [Log10(E/MeV)]\n'
yield_header += 'Column 1 Annihilation Yield [MeV^{-1}]\n'

dp = DensityProfile.create(halo_model)
jp = LoSIntegralFn.create(halo_model)

psi_edge = np.radians(10**np.linspace(np.log10(0.01),np.log10(45.),200))
psi = 0.5*(psi_edge[1:] + psi_edge[:-1])
jval = jp(psi)

for m in massv:

    mass = 10**m*Units.gev
    sp = DMChanSpectrum(args.channel,mass=mass)

    loge = np.linspace(-1.0,4.0,16*5+1)
    loge += np.log10(Units.gev)

    yld = sp.dnde(loge)

    flux = 1./(8.*np.pi)*sigmav*np.power(mass,-2)*sp.dnde(loge)
    flux[flux<=0] = 0

    e2flux = flux*10**(2*loge)

    e2flux = np.outer(jval,e2flux)
    flux = np.outer(jval,flux)

    x,y = np.meshgrid(loge,psi,ordering='ij')

    h = copy.copy(flux_header)
    h += 'Mass                 = %10.5g [GeV]\n'%10**m
    h += 'Cross Section        = %10.5g [cm^{3} s^{-1}]\n'%(sigmav/Units.cm3_s)
    h += 'Annihilation Channel = %s\n'%(args.channel)

    h += 'Halo rs       = %10.5g [kpc]\n'%(jp._dp._rs/Units.kpc)
    h += 'Halo rhos     = %10.5g [GeV cm^{-3}]\n'%(jp._dp._rhos/Units.gev_cm3)
    h += 'Halo Distance = %10.5g [kpc]\n'%(jp._dist/Units.kpc)
    h += 'Halo Model    = %s'%(dp.__class__.__name__)

    np.savetxt('flux_%s_%s_m%06.3f.txt'%(args.halo_model,args.channel,m),
               np.array((np.ravel(x)-np.log10(Units.mev),np.ravel(y),
                         np.ravel(e2flux)/Units.mev,
                         np.ravel(flux)/(1./Units.mev))).T,
               fmt='%12.5g',
               header=h)

    h = copy.copy(yield_header)
    h += 'Mass                 = %10.5g [GeV]\n'%10**m
    h += 'Cross Section        = %10.5g [cm^{3} s^{-1}]\n'%(sigmav/Units.cm3_s)
    h += 'Annihilation Channel = %s\n'%(args.channel)

    np.savetxt('yield_%s_m%06.3f.txt'%(args.channel,m),
               np.array((loge-np.log10(Units.mev),yld/Units._mev)).T,
               fmt='%12.5g',header=h)

plt.figure()

plt.plot(loge-np.log10(Units.gev),e2flux[0,:]/Units.erg)


plt.gca().set_yscale('log')

plt.figure()
plt.plot(loge-np.log10(Units.gev),sp.e2dnde(loge)/Units.gev)

plt.gca().set_yscale('log')

plt.gca().grid(True)

