#! /usr/bin/env python

import os

#os.environ['CUSTOM_IRF_DIR']='/u/gl/mdwood/ki10/analysis/custom_irfs/'
#os.environ['CUSTOM_IRF_NAMES']='P6_v11_diff,P7CLEAN_V4,P7CLEAN_V4MIX,P7CLEAN_V4PSF,P7SOURCE_V4,P7SOURCE_V4MIX,P7SOURCE_V4PSF,P7ULTRACLEAN_V4,P7ULTRACLEAN_V4MIX,P7ULTRACLEAN_V4PSF'

import sys
import re
import bisect
import pyfits
import healpy
import numpy as np
import matplotlib.pyplot as plt
from gammatools.core.histogram import *
from gammatools.core.plot_util import *

import gammatools.fermi.psf_model 
import argparse

from gammatools.fermi.irf_util import *
    
usage = "usage: %(prog)s [options]"
description = ""
parser = argparse.ArgumentParser(usage=usage,description=description)

parser.add_argument('files', nargs='+')

parser.add_argument('--prefix', default = 'prefix_', 
                  help = 'Set the output file prefix.')

parser.add_argument('--load_from_file', default = False, 
                    action='store_true',
                    help = 'Load IRFs from FITS.')

parser.add_argument('--show', default = False, 
                    action='store_true',
                    help = 'Show plots interactively.')

IRFManager.add_arguments(parser)

args = parser.parse_args()


ft = FigTool(marker=['None'],hist_style='line')




labels = args.files

energy_label = 'Energy [log$_{10}$(E/MeV)]'
costh_label = 'Cos $\\theta$'
acceptance_label = 'Acceptance [m$^2$ sr]'
effarea_label = 'Effective Area [m$^2$]'

psb_label = '68% PSF Containment [deg]'
psf68_label = '68% PSF Containment [deg]'
psf68_ratio_label = '68% PSF Containment Ratio'
psf95_label = '95% PSF Containment [deg]'
psf95_ratio_label = '95% PSF Containment Ratio'

irf_models = []
for arg in args.files:

    m = IRFManager.create(arg,args.load_from_file,args.irf_dir)
    m.dump()
    irf_models.append(m)

    
for i, irfm in enumerate(irf_models):
    continue
    
    for j, irf in enumerate(irfm._irfs):

        irf0 = irf_models[0]._irfs[j]
        
        fig = ft.create('psf_table_%02i'%(i),nax=(3,2),figscale=1.4)
        fig[0].set_title('score')
        fig[0].add_hist(irf._psf._score_hist)
        fig[1].set_title('stail')
        fig[1].add_hist(irf._psf._stail_hist)
        fig[2].set_title('gcore')
        fig[2].add_hist(irf._psf._gcore_hist)
        fig[3].set_title('gtail')
        fig[3].add_hist(irf._psf._gtail_hist)
        fig[4].set_title('fcore')
        fig[4].add_hist(irf._psf._fcore_hist)
        fig.plot()

        if i == 0: continue
        
        fig = ft.create('psf_table_ratio_%02i'%(i),nax=(3,2),figscale=1.4)
        fig[0].set_title('score')
        fig[0].add_hist(irf._psf._score_hist/irf0._psf._score_hist)
        fig[1].set_title('stail')
        fig[1].add_hist(irf._psf._stail_hist/irf0._psf._stail_hist)
        fig[2].set_title('gcore')
        fig[2].add_hist(irf._psf._gcore_hist/irf0._psf._gcore_hist)
        fig[3].set_title('gtail')
        fig[3].add_hist(irf._psf._gtail_hist/irf0._psf._gtail_hist)
        fig[4].set_title('fcore')
        fig[4].add_hist(irf._psf._fcore_hist/irf0._psf._fcore_hist)
        fig.plot()
        
    

#x = np.linspace(2.0,3.0,100)
#y = 0.5*np.ones(100)    

#print irf_models[0].psf_quantile(x,y)
#print irf_models[0]._psf[0].quantile(2.0,0.5)

#sys.exit(0)
    
acc_hists = []
effarea_hists = []
psf68_hists = []
psf95_hists = []
psfb_mean_hists = []
psfb_median_hists = []
psfb_peak_hists = []

#fig, axes = plt.subplots(2,len(irf_models))

#acc_fig = ft.create('acc')
#psf_fig = ft.create('psf')

loge_axis = Axis.create(1.00,6.50,44,label=energy_label)
cth_axis = Axis.create(0.2,1.0,32,label=costh_label)

for k, irf in enumerate(irf_models):
    hpsf68 = Histogram2D(loge_axis,cth_axis)
    hpsf95 = Histogram2D(loge_axis,cth_axis)
    hpsfb = Histogram2D(loge_axis,cth_axis)
    hacc = Histogram2D(loge_axis,cth_axis)
    heffarea = Histogram2D(loge_axis,cth_axis)         
    heffarea._counts = irf.aeff(*heffarea.center()).reshape(heffarea.shape())
    hpsf68._counts = irf.psf_quantile(*hpsf68.center()).reshape(hpsf68.shape())
    hpsf95._counts = irf.psf_quantile(*hpsf95.center(),
                                       frac=0.95).reshape(hpsf95.shape())
    hpsfb_mean = \
        HistogramND.createFromFn([loge_axis,cth_axis],
                                 lambda x, y: irf.fisheye(x,y,ctype='mean'))
    hpsfb_median = \
        HistogramND.createFromFn([loge_axis,cth_axis],
                                 lambda x, y: irf.fisheye(x,y,ctype='median'))
    hpsfb_peak = \
        HistogramND.createFromFn([loge_axis,cth_axis],
                                 lambda x, y: irf.fisheye(x,y,ctype='peak'))

    hpsfb_mean = hpsfb_mean.abs()
    hpsfb_median = hpsfb_median.abs()
    hpsfb_peak = hpsfb_peak.abs()
        
    hacc = heffarea*2.*np.pi*hacc.yaxis().width[np.newaxis,:]
    acc_hists.append(hacc)
    psf68_hists.append(hpsf68)
    psf95_hists.append(hpsf95)
    psfb_mean_hists.append(hpsfb_mean)
    psfb_median_hists.append(hpsfb_median)
    psfb_peak_hists.append(hpsfb_peak)
    effarea_hists.append(heffarea)
    
    fig = ft.create('%s_effarea'%(labels[k]),
                    title=labels[k],zlabel=effarea_label,
                    xlabel=energy_label,costh_label=costh_label)

    fig[0].add_hist(heffarea)
    
    fig.plot()

    fig = ft.create('%s_psf68'%(labels[k]),
                    title=labels[k],zlabel=psf68_label,
                    xlabel=energy_label,costh_label=costh_label,
                    logz=True)

    fig[0].add_hist(hpsf68)
    
    fig.plot()

    fig = ft.create('%s_psf95'%(labels[k]),
                    title=labels[k],zlabel=psf95_label,
                    xlabel=energy_label,costh_label=costh_label,
                    logz=True)

    fig[0].add_hist(hpsf95)
    
    fig.plot()

    continue
    

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title(labels[k])
    h = effarea_hists[k]/effarea_hists[0]
    im = h.plot(ax=ax)
    cb = plt.colorbar(im)    
    cb.set_label('Effective Area Ratio')
    
    ax.grid(True)
    ax.set_xlabel(energy_label)
    ax.set_ylabel(costh_label)
    
    fig.savefig(opts.prefix + '%s_effarea_ratio.png'%(labels[k]))

    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title(labels[k])
    im = hacc.plot(ax=ax)    
    cb = plt.colorbar(im)
    cb.set_label('Acceptance [m$^2$ sr]')

    ax.grid(True)
    ax.set_xlabel(energy_label)
    ax.set_ylabel(costh_label)
    
    fig.savefig(opts.prefix + '%s_acceptance.png'%(labels[k]))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title(labels[k])
    h = acc_hists[k]/acc_hists[0]
    im = h.plot(ax=ax)
    cb = plt.colorbar(im)    
    cb.set_label('Acceptance Ratio')
    
    ax.grid(True)
    ax.set_xlabel(energy_label)
    ax.set_ylabel(costh_label)
    
    fig.savefig(opts.prefix + '%s_acceptance_ratio.png'%(labels[k]))
    

    
    fig = plt.figure()

    ax = fig.add_subplot(111)
#    ax = psf_fig.add_subplot(2,len(irf_models),k+1+len(irf_models))
    ax.set_title(labels[k])
    h = psf_hists[k]/psf_hists[0]
    im = h.plot(ax=ax)
    plt.colorbar(im)
    
    ax.grid(True)
    ax.set_xlabel(energy_label)
    ax.set_ylabel(costh_label)
    
    fig.savefig(opts.prefix + '%s_psf68_ratio.png'%(labels[k]))
    
    
fig = ft.create('acc',legend_loc='lower right',figstyle='ratio2',
                xlabel=energy_label,ylabel=acceptance_label,
                hist_xerr=False)

for i in range(len(acc_hists)):
    hm = acc_hists[i].marginalize(1)
    fig[0].add_hist(hm,label=labels[i],marker='o')
    
#plt.gca().legend(prop={'size':8},loc='lower right')

fig.plot()
    
def make_projection_plots(hists,cut_label,cut_dim,cuts,figname,**kwargs):
    fig = ft.create(figname,nax=4,**kwargs)
    for i in range(len(hists)):

        for j in range(len(cuts)):
#            axes.flat[j].set_title('%s = %.2f'%(cut_label,cuts[j]))
            fig[j].set_title('%s = %.2f'%(cut_label,cuts[j]))
            hm = hists[i].sliceByValue(cut_dim,cuts[j])
            fig[j].add_hist(hm,label=labels[i],linestyle='-',
                            marker='o')

    fig.plot()
            
#    for j, ax in enumerate(axes.flat):
#        ax.set_xlim(hm0[j]._xedges[0],hm0[j]._xedges[-1])
#        ax.legend(prop={'size':8})    
#        if logy: ax.set_yscale('log')
#    fig.savefig(figname,bbox_inches='tight')

common_kwargs = { 'hist_xerr': False, 'figscale' : 1.4 }

make_projection_plots(psfb_mean_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'psfb_mean_egy',
                      xlabel=energy_label,
                      ylabel='Mean Fisheye Correction [deg]',
                      ylim=[1E-3,1E2],
                      yscale='log',legend_loc='upper right',**common_kwargs)

make_projection_plots(psfb_median_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'psfb_median_egy',
                      xlabel=energy_label,
                      ylabel='Median Fisheye Correction [deg]',
                      ylim=[1E-3,1E2],
                      yscale='log',legend_loc='upper right',**common_kwargs)

make_projection_plots(psfb_peak_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'psfb_peak_egy',
                      xlabel=energy_label,
                      ylabel='Peak Fisheye Correction [deg]',
                      ylim=[1E-3,1E2],
                      yscale='log',legend_loc='upper right',**common_kwargs)

plt.show()

make_projection_plots(psf68_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'psf68_egy',
                      xlabel=energy_label,ylabel=psf68_label,
                      yscale='log',legend_loc='upper right',**common_kwargs)

make_projection_plots(psf68_hists,'log$_{10}$(E/MeV)',0,[2.0,3.0,4.0,5.0],
                      'psf68_costh',xlabel=costh_label,ylabel=psf68_label,
                      legend_loc='upper right',**common_kwargs)

make_projection_plots(psf95_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'psf95_egy',
                      xlabel=energy_label,ylabel=psf95_label,
                      yscale='log',legend_loc='upper right',**common_kwargs)

make_projection_plots(psf95_hists,'log$_{10}$(E/MeV)',0,[2.0,3.0,4.0,5.0],
                      'psf95_costh',xlabel=costh_label,ylabel=psf95_label,
                      legend_loc='upper right',**common_kwargs)

#make_projection_plots(psf_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
#                      'psf68_ratio_egy',xlabel=energy_label,ylabel=psf_ratio_label)
#make_projection_plots(psf_hists,'log$_{10}$(E/MeV)',0,[2.0,3.0,4.0,5.0],
#                      costh_label,psf_ratio_label,'psf68_ratio_costh')


make_projection_plots(effarea_hists,'Cos $\\theta$',1,[1.0,0.8,0.6,0.4],
                      'effarea_egy',xlabel=energy_label,ylabel=effarea_label,
                      **common_kwargs)

make_projection_plots(effarea_hists,'log$_{10}$(E/MeV)',0,[2.0,3.0,4.0,5.0],
                      'effarea_costh',xlabel=costh_label,ylabel=effarea_label,
                      **common_kwargs)


if args.show: plt.show()
    
sys.exit(0)
#irf = IRFManager(args[0],args[1])

h0 = Histogram2D([1.5,5.5],40,[0.4,1.0],24)
h1 = Histogram2D([1.5,5.5],40,[0.4,1.0],24)
h2 = Histogram2D([1.5,5.5],40,[0.4,1.0],24)

for ix, x in enumerate(h0._x):
    for iy, y in enumerate(h0._y):
        h0._counts[ix,iy] = irf._psf.quantile(x,y)

irf._psf._interpolate_density = False
        
for ix, x in enumerate(h0._x):
    for iy, y in enumerate(h0._y):
        h1._counts[ix,iy] = irf._psf.quantile(x,y)


h2._counts = (h0._counts - h1._counts)/h1._counts
        
plt.figure()
h0.plot()
plt.figure()
h1.plot()
plt.figure()
h2.plot(vmin=-0.1,vmax=0.1)
plt.colorbar()

plt.figure()

x = np.linspace(1.5,5.5,100)
y0 = []
y1 = []



irf._psf._interpolate_density = True
for t in x: y0.append(irf._psf.quantile(t,0.6,0.68))
irf._psf._interpolate_density = False
for t in x: y1.append(irf._psf.quantile(t,0.6,0.68))

y0 = np.array(y0)
y1 = np.array(y1)


plt.plot(x,(y0-y1)/y1)

plt.plot()

plt.show()
#pyirf = IRFManager.createFromIRF('P7SOURCE_V6MC::FRONT')


print irf._psf.quantile(2.0,0.5)



print irf._psf.quantile(2.0,0.5)

sys.exit(1)

dtheta = np.linspace(0,3,100)

plt.figure()

loge = 1.75 
cth = irf._psf._center[0][4]

plt.plot(dtheta,irf.psf(dtheta,loge,cth),color='b')
plt.plot(dtheta,irf.psf(dtheta,loge+0.125,cth),color='g')
plt.plot(dtheta,irf.psf(dtheta,loge+0.25,cth),color='r')

plt.plot(dtheta,np.power(np.pi/180.,2)*pyirf.psf(dtheta,loge,cth),
         linestyle='--',color='b')
plt.plot(dtheta,np.power(np.pi/180.,2)*pyirf.psf(dtheta,loge+0.125,cth),
         linestyle='--',color='g')
plt.plot(dtheta,np.power(np.pi/180.,2)*pyirf.psf(dtheta,loge+0.25,cth),
         linestyle='--',color='r')


#plt.gca().set_yscale('log')
plt.gca().set_xscale('log')
plt.gca().grid(True)

plt.show()

h0 = Histogram([0,4.0],200)
h1 = Histogram([0,4.0],200)

h0._counts = irf.psf(h0._x,loge,cth)*h0._x*2*np.pi*h0._width
h1._counts = np.power(np.pi/180.,2)*pyirf.psf(h1._x,loge,cth)*h1._x*2*np.pi*h1._width

plt.figure()

h0.cumulative()
h1.cumulative()

h0.plot()
h1.plot()

plt.gca().grid(True)

plt.show()
