#!/usr/bin/env python

"""
@file  histogram.py

@brief Python classes encapsulating 1D and 2D histograms."

@author Matthew Wood <mdwood@slac.stanford.edu>
"""

__author__   = "Matthew Wood <mdwood@slac.stanford.edu>"
__date__     = "$Date: 2013/10/20 23:59:49 $"
__revision__ = "$Revision: 1.30 $, $Author: mdwood $"

import sys
import numpy as np
import copy
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
from scipy.optimize import brentq
from util import *

def makeHistModel(xedge,ncount,min_count=5):

    if np.sum(ncount) == 0: return Histogram(xedge)

    h = Histogram(xedge)
    h._counts = copy.deepcopy(ncount)
    h._var = copy.deepcopy(ncount)
    h = h.rebin_mincount(min_count)

    ncum = np.concatenate(([0],np.cumsum(h._counts)))
    fn = UnivariateSpline(h.edges(),ncum,s=0,k=2)
    mu_count = fn(xedge[1:])-fn(xedge[:-1])
    mu_count[mu_count<0] = 0

    return Histogram(xedge,counts=mu_count,var=copy.deepcopy(mu_count))

class HistogramND(object):
    """
    N-dimensional histogram class.
    """

    def __init__(self, axes, label = '__nolabel__', counts=None, var=None):


        self._axes = []

        for ax in axes:
            if isinstance(ax,Axis): self._axes.append(copy.deepcopy(ax))
            else: self._axes.append(Axis(ax))

        if counts is None:
            shape = []
            for ax in self._axes: shape.append(ax.nbins())
            self._counts = np.zeros(shape=shape)
        else: self._counts = copy.deepcopy(counts)

        if var is None: self._var = np.zeros(shape=self._counts.shape)
        else: self._var = copy.deepcopy(var)

        self._ndim = self._counts.ndim
        self._dims = np.array(range(self._ndim),dtype=int)

    def axes(self):
        return self._axes

    def fill(self,z,w=1.0):
        """
        Fill the histogram from an NxM array of points where M is the
        dimension of this histogram and N is the number of points.

        @param z: Array of NxM points.
        @param w: Array of N bin weights.
        @return:
        """

        z = np.array(z,ndmin=2)

        edges = []
        for i in self._dims: edges.append(self._axes[i].edges())

        counts = np.histogramdd(z.T,bins=edges)[0]
        var = np.histogramdd(z.T,bins=edges)[0]

        self._counts += counts
        self._var += var

    def project(self,pdims):
        pdims = np.array(pdims,ndmin=1,copy=True)

        mdims = np.setdiff1d(self._dims,pdims)
        axes = []
        new_shape = []
        for i in pdims:
            axes.append(self._axes[i])
            new_shape.append(self._axes[i].nbins())

        c = np.apply_over_axes(np.sum,self._counts,mdims).reshape(new_shape)
        v = np.apply_over_axes(np.sum,self._var,mdims).reshape(new_shape)

        return HistogramND.create(axes,c,v)

    def normalize(self):

        norm = np.sum(self._counts)
        if norm != 0: inorm = 1./norm
        else: inorm = 0

        c = self._counts*inorm
        v = self._var*inorm**2

        return HistogramND.create(self._axes,c,v)

    def marginalize(self,mdims):
        mdims = np.array(mdims,ndmin=1,copy=True)

        pdims = np.setdiff1d(self._dims,mdims)
        return self.project(pdims)

    def cumulative(self,dims=None):

        if dims is None: dims = self._dims
        else: dims = np.array(dims,ndmin=1,copy=True)

        c = np.apply_over_axes(np.cumsum,self._counts,dims)
        v = np.apply_over_axes(np.cumsum,self._var,dims)

        return HistogramND.create(self._axes,c,v)

    def sum(self):

        return np.array([np.sum(self._counts),np.sqrt(np.sum(self._var))])

    def slice(self,sdims,dim_index):
        sdims = np.array(sdims,ndmin=1,copy=True)
        dim_index = np.array(dim_index,ndmin=1,copy=True)

        axes= []
        index = []
        new_edges = []
        new_shape = []

        for i in self._dims:
            if not i in sdims:
                new_edges.append(self._axes[i].edges())
                new_shape.append(self._axes[i].nbins())
            index.append(range(self._axes[i].nbins()))

        for i, idim in enumerate(sdims):
            if idim >= self._ndim or dim_index[i] >= self._axes[idim].nbins():
                raise ValueError('Dimension or Index out of range')

            index[idim] = [dim_index[i]]


#        print self._counts.shape

        ix = np.ix_(*index)

#        print 'ix: ', ix
#        print 'new_shape: ', new_shape

        c = self._counts[ix].reshape(new_shape)
        v = self._var[ix].reshape(new_shape)


#        print 'shape ', c.shape
#        print 'new_edges ', new_edges

        return HistogramND.create(new_edges,c,v)

    def __add__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, HistogramND):
            o._counts += x._counts
            o._var += x._var
        else:
            o._counts += x
            o._var += x

        return o

    @staticmethod
    def create(axes,c,v):
        ndim = len(axes)
        if ndim == 1: return Histogram(axes[0],counts=c,var=v)
        elif ndim == 2: return Histogram2D(axes[0],axes[1],counts=c,var=v)
        else: return HistogramND(axes,counts=c,var=v)

    @staticmethod
    def createFromTree(t,vars,edges,cut='',fraction=1.0,
                       label = '__nolabel__'):

        nentries=t.GetEntries()
        first_entry = min(int((1.0-fraction)*nentries),nentries)
        nentries = nentries - first_entry

        x = []
        for v in vars: x.append(get_vector(t,v,cut,nentries,first_entry))
        z = np.vstack(x)

        h = HistogramND(edges)
        h.fill(z)

        return h

class HistogramIterator(object):
    """Iterator module that steps over the bins of a one-dimensional
    histogram."""

    def __init__(self,ibin,h):
        self._ibin = ibin
        self._h = h

    def set_counts(self,counts):
        self._h._counts[self._ibin] = counts

    def bin(self):
        return self._ibin

    def counts(self):
        return self._h.counts(self._ibin)

    def center(self):
        return self._h.axis().center()[self._ibin]

    def lo_edge(self):
        return self._h.axis().edges()[self._ibin]

    def hi_edge(self):
        return self._h.axis().edges()[self._ibin+1]

    def next(self):

        self._ibin += 1

        if self._ibin == self._h.nbins():
            raise StopIteration
        else:
            return self

    def __iter__(self):
        return self


class Axis(object):

    def __init__(self,edges,nbins=None,label=None):
        self._label = label

        edges = np.array(edges,copy=True)

        if not nbins is None:
            edges = np.linspace(edges[0],edges[-1],nbins+1)

        if len(edges) < 2:
            raise ValueError("Axis must be initialized with at least two "
                             "bin edges.")

        self._edges = edges
        self._nbins = len(edges)-1
        self._xmin = self._edges[0]
        self._xmax = self._edges[-1]
        self._center = 0.5*(self._edges[1:] + self._edges[:-1])
        self._err = 0.5*(self._edges[1:] - self._edges[:-1])
        self._width = 2*self._err

    @staticmethod
    def create(lo,hi,nbin):
        return Axis(np.linspace(lo,hi,nbin+1))

    def nbins(self):
        return self._nbins

    def lo_edge(self):
        return self._edges[0]

    def hi_edge(self):
        return self._edges[-1]

    def edges(self):
        return self._edges

    def width(self):
        return self._width

    def center(self):
        return self._center

    def bin_width(self):
        return self._width

    def valToBin(self,x):
        ibin = np.digitize(np.array(x,ndmin=1),self._edges)-1
        return ibin


class Histogram(object):
    """One-dimensional histogram class.  Each bin is assigned both a
    content value and an error.  Non-equidistant bin edges can be
    defined with an input bin edge array.  Supports multiplication,
    addition, and division by a scalar or another histogram object."""

    default_draw_style = { 'marker' : None,
                           'color' : None,
                           'drawstyle' : 'default',
                           'markerfacecolor' : None,
                           'markeredgecolor' : None,
                           'linestyle' : None,
                           'linewidth' : 1,
                           'label' : None }

    default_style = { 'hist_style' : 'errorbar',
                      'xerr' : True, 'yerr' : True,
                      'max_frac_error' : None }


    def __init__(self,axis,label = '__nolabel__',
                 counts=None,var=None,style=None):
        """
        Create a histogram object.
                
        @param axis:  Axis object or array of bin edges.
        @param label: Label for this histogram.
        @param counts: Vector of bin values.  The histogram will be 
        initialized with this vector when this argument is defined.
        @param var: Vector of bin variances.
        @param style: Style dictionary.
        @return:
        """
        
        if isinstance(axis,Axis): self._axis = copy.deepcopy(axis)
        else: self._axis = Axis(axis)

        if not counts is None: self._counts = counts
        else: self._counts = np.zeros((self._axis.nbins()))

        if not var is None: self._var = var
        else: self._var = np.zeros((self._axis.nbins()))

        self._underflow = 0
        self._overflow = 0

        self._style = copy.deepcopy(dict(Histogram.default_style.items() +
                                         Histogram.default_draw_style.items()))
        if not style is None: update_dict(self._style,style)
        self._style['label'] = label

    def iterbins(self):
        """Return an iterator object that steps over the bins in this
        histogram."""
        return HistogramIterator(-1,self)

    @staticmethod
    def createEfficiencyHistogram(htot,hcut,label = '__nolabel__'):
        """Create a histogram of cut efficiency."""

        h = Histogram(htot.axis().edges(),htot.nbins(),label)
        eff = hcut._counts/htot._counts

        h._counts = eff
        h._var = eff*(1-eff)/htot._counts

        return h

    @staticmethod
    def createFromTree(t,varname,cut,hdef=None,fraction=0.0,
                       label = '__nolabel__'):

        from ROOT import gDirectory

        draw = '%s>>hist'%(varname)

        if not hdef is None:
            draw += '(%i,%f,%f)'%(hdef[0],hdef[1],hdef[2])

        nevent = t.GetEntries()
        first_entry = int(nevent*fraction)

        t.Draw(draw,cut,'goff',nevent,first_entry)
        h = gDirectory.Get('hist')
        h.SetDirectory(0)
        return Histogram.createFromTH1(h,label)

    @staticmethod
    def createFromTH1(hist,label = '__nolabel__'):
        n = hist.GetNbinsX()
        xmin = hist.GetBinLowEdge(1)
        xmax = hist.GetBinLowEdge(n+1)

        h = Histogram(np.linspace(xmin,xmax,n+1),label)
        h._counts = np.array([hist.GetBinContent(i) for i in range(1, n + 1)])
        h._var = np.array([hist.GetBinError(i)**2 for i in range(1, n + 1)])
        h._underflow = hist.GetBinContent(0)
        h._overflow = hist.GetBinContent(n+1)

        return h

    def update_style(self,style):
        update_dict(self._style,style)

    def axis(self):
        return self._axis

    def label(self):
        return self._style['label']

    def bin_width(self):
        return self._axis.bin_width()

    def errorbar(self, label_rotation=0,
                 label_alignment='center', ax=None, msk=None,
                 counts=None, x=None,**kwargs):
        """
        Draw this histogram in the 'errorbar' style.

        All additional keyword arguments will be passed to
        :func:`matplotlib.pyplot.errorbar`.
        """
        style = copy.deepcopy(self._style)
        style.update(kwargs)

        if ax is None: ax = plt.gca()
        if counts is None: counts = self._counts
        if x is None: x = self._axis.center()

        if msk is None:
            msk = np.empty(len(counts),dtype='bool'); msk.fill(True)

        xerr = None
        yerr = None

        if style['xerr']: xerr = self._axis.width()[msk]/2.
        if style['yerr']: yerr = np.sqrt(self._var[msk])
        if not style.has_key('fmt'): style['fmt'] = '.'

        clear_dict_by_keys(style,Histogram.default_draw_style.keys(),False)
        clear_dict_by_vals(style,None)

        errorbar = ax.errorbar(x[msk], counts[msk],xerr=xerr,yerr=yerr,**style)
        self._prepare_xaxis(label_rotation, label_alignment)
        return errorbar

    def hist(self,ax=None,counts=None,**kwargs):
        """Plot this histogram using the 'hist' matplotlib method."""
        if ax is None: ax = plt.gca()
        if counts is None: counts = self._counts

        ax.hist(self._axis.center(), self._axis.nbins(),
                range=[self._axis.lo_edge(),self._axis.hi_edge()],
                weights=counts,**kwargs)


    def plot(self,ax=None,msk=None,overflow=False,**kwargs):

        style = copy.deepcopy(self._style)
        style.update(kwargs)

        if ax is None: ax = plt.gca()
        if msk is None:
            msk = np.empty(self._axis.nbins(),dtype='bool')
            msk.fill(True)

        if overflow:
            c = copy.deepcopy(self._counts)
            c[0] += self._underflow
            c[-1] += self._overflow
        else:
            c = self._counts

        if not style['max_frac_error'] is None:
            frac_err = np.sqrt(self._var)/self._counts
            msk = frac_err <= style['max_frac_error']

        if style['hist_style'] == 'errorbar':
            return self.errorbar(ax=ax,counts=c,msk=msk,**style)
        elif style['hist_style'] == 'line':

            style['marker'] = 'None'
            style['xerr'] = False
            style['yerr'] = False
            style['fmt'] = '-'
            return self.errorbar(ax=ax,counts=c,msk=msk,**style)
        elif style['hist_style'] == 'filled':

            draw_style = copy.deepcopy(style)
            clear_dict_by_keys(draw_style,
                               Histogram.default_draw_style.keys(),False)
            clear_dict_by_vals(draw_style,None)
            draw_style['linewidth'] = 0
            del draw_style['linestyle']
            del draw_style['marker']
            del draw_style['drawstyle']

            return self.hist(ax=ax,histtype='bar',counts=c,**draw_style)
        elif style['hist_style'] == 'step':

            c = np.concatenate(([0],c,[0]))
            edges = np.concatenate((self._axis.edges(),
                                    [self._axis.edges()[-1]]))
#            msk = np.concatenate((msk,[True]))
            style['xerr'] = False
            style['yerr'] = False
            style['fmt'] = '-'
            style['drawstyle'] = 'steps-pre'
            style['marker'] = 'None'
            return self.errorbar(ax=ax,counts=c,
                                 x=edges,**style)

        else:
            print 'Unrecognized style ', style
            sys.exit(1)

    def clear(self):
        self._counts[:] = 0
        self._var[:] = 0

    def scale_density(self,fn):

        h = copy.deepcopy(self)

        for i in range(self.axis().nbins()):
            xhi = fn(self.axis().edges()[i+1])
            xlo = fn(self.axis().edges()[i])

            area = xhi - xlo

            h._counts[i] /= area
            h._var[i] /= area**2

        return h

    def nbins(self):
        """Return the number of bins in this histogram."""
        return self._axis.nbins()

    def counts(self,ibin=None):
        if ibin is None: return self._counts
        else: return self._counts[ibin]

    def center(self):
        """Return array of bin centers."""
        return self._axis.center()

    def edges(self):
        """Return array of bin edges."""
        return self._axis.edges()

    def width(self):
        """Return array of bin edges."""
        return self._axis.width()

    def underflow(self):
        return self._underflow

    def overflow(self):
        return self._overflow

    def err(self,ibin=None):
        if ibin == None: return np.sqrt(self._var)
        else: return np.sqrt(self._var[ibin])

    def var(self,ibin=None):
        if ibin == None: return self._var
        else: return self._var[ibin]

    def sum(self,overflow=False):
        """Return the sum of counts in this histogram."""

        s = 0
        if overflow:
            s = np.sum(self._counts) + self._overflow + self._underflow
        else:
            s = np.sum(self._counts)

        return np.array([s,np.sqrt(np.sum(self._var))])

    def cumulative(self,lhs=True):
        """Convert this histogram to its cumulative distribution."""

        if lhs:
            counts = np.cumsum(self._counts)
            var = np.cumsum(self._var)
        else:
            counts = np.cumsum(self._counts[::-1])[::-1]
            var = np.cumsum(self._var[::-1])[::-1]

        return Histogram(self._axis.edges(),label=self.label(),
                         counts=counts,var=var)

    def getBinByValue(self,x):
        return np.argmin(np.abs(self._x-x))

    def interpolate(self,x):

        x = np.array(x,ndmin=1)
        wx = self._axis.bin_width()
        x0 = self._axis.edges()
        z = self._counts

        ix = np.digitize(x,x0[:-1]+0.5*wx)-1
        xs = (x - x0[ix] - 0.5*wx[ix])/wx[ix]

        ix[ix > x0.shape[0] -3 ] = x0.shape[0] - 3

        c = (self._counts[ix]*(1-xs) + self._counts[ix+1]*xs)
        v = (self._var[ix]*(1-xs) + self._var[ix+1]*xs)

        if len(x)==1:
            return np.array([c[0],np.sqrt(v)[0]])
        else:
            return np.vstack((c,np.sqrt(v)))

        from util import interpolate

        c = interpolate(self._axis.edges(),self._counts,x)

        return c

    def normalize(self):

        s = np.sum(self._counts)

        counts = self._counts/s
        var = self._var/s**2

        return Histogram(self._axis,label=self.label(),
                         counts=counts,var=var)

    def quantile(self,fraction=0.68,**kwargs):

        import stats

        return stats.HistQuantile(self).eval(fraction,**kwargs)

    def chi2(self,hmodel):

        msk = self._var > 0
        diff = self._counts[msk] - hmodel._counts[msk]
        chi2 = np.sum(np.power(diff,2)/self._var[msk])
        ndf = len(msk[msk==True])
        return (chi2,ndf)

    def fill(self,x,w=1,var=None):
        """
        Add counts to the histogram at the coordinates given in the
        array x.  The weight assigned to each element of x can be
        optionally specified by providing a scalar or vector for the w
        argument.
        """
        w = np.array(w)

        if var is None: var = w

        if w.ndim == 1:

            c1 = np.histogram(x,bins=self._axis.edges(),weights=w)[0]
            c2 = np.histogram(x,bins=self._axis.edges(),weights=var)[0]

            self._counts += c1
            self._var += c2

            if np.any(x>=self._axis.hi_edge()):
                self._overflow += np.sum(w[x>=self._axis.hi_edge()])
            if np.any(x<self._axis.lo_edge()):
                self._underflow += np.sum(w[x<self._axis.lo_edge()])

        else:
            c = np.histogram(x,bins=self._axis.edges())[0]

            self._counts += w*c
            self._var += var*c

            if np.any(x>=self._axis.hi_edge()):
                self._overflow += np.sum(x>=self._axis.hi_edge())
            if np.any(x<self._axis.lo_edge()):
                self._underflow += np.sum(x<self._axis.lo_edge())


    def rebin_mincount(self,min_count,max_bins=None):
        """Return a rebinned copy of this histogram such that all bins
        have an occupation of at least min_count.
        
        Parameters
        ----------

        min_count : int
            Minimum occupation of each bin.

        max_bins : int
            Maximum number of bins that can be combined.
        
        """

        bins = []
#        cum_counts = np.cumsum(self._counts)

        ibin = 0
        while ibin < self._axis.nbins():

            jbin = ibin
            s = 0
            while jbin < self._axis.nbins():
                s += self._counts[jbin]
                if s >= min_count:
                    break
                if max_bins is not None and jbin-ibin+1 > max_bins:
                    break

                jbin += 1

            jbin = min(jbin,self._axis.nbins()-1)
            bins.append(jbin-ibin+1)
            ibin = jbin+1

        return self.rebin(bins)

    def rebin_range(self,n=2,xmin=0,xmax=0):

        bins = []

        i = 0
        while i < self._axis.nbins():

            if xmin != xmax and self._axis.center()[i] >= xmin and \
                    self._axis.center()[i] <= xmax:

                m = n
                if i+n > self._axis.nbins():
                    m = self._axis.nbins()-i

                i+= m
                bins.append(m)
            else:
                i+= 1
                bins.append(1)

        return self.rebin(bins)


    def rebin(self,bins=2):

        bins = np.asarray(bins)

        if bins.ndim == 0:
            bin_index = [i for i in range(0,self._axis.nbins(),bins)]
            bin_index.append(self._axis.nbins())
            bin_index = np.array(bin_index)
        else:
            if np.sum(bins) != self._axis.nbins():
                raise ValueError("Sum of bins is not equal to histogram bins.")

            bin_index = np.concatenate((np.array([0],dtype='int'),
                                        np.cumsum(bins,dtype='int')))

        xedges = self._axis.edges()[bin_index]

        nbins = len(xedges)-1
        counts = np.zeros(nbins)
        var = np.zeros(nbins)

        csum = np.concatenate(([0],np.cumsum(self._counts)))
        vsum = np.concatenate(([0],np.cumsum(self._var)))

        counts = csum[bin_index[1:]]-csum[bin_index[:-1]]
        var = vsum[bin_index[1:]]-vsum[bin_index[:-1]]

        return Histogram(xedges,label=self.label(),counts=counts,var=var)

    def residual(self,h):
        """
        Generate a residual histogram.

        @param h: Input histogram
        @return: Residual histogram
        """
        o = copy.deepcopy(self)
        o -= h
        return o.divide(h)


    def divide(self,h):
        o = copy.deepcopy(self)

        y1 = self._counts
        y2 = h._counts
        y1_var = self._var
        y2_var = h._var

        msk = ((y1!=0) & (y2!=0))

        o._counts[~msk] = 0.
        o._var[~msk] = 0.

        o._counts[msk] = y1[msk] / y2[msk]
        o._var[msk] = (y1[msk] / y2[msk])**2
        o._var[msk] *= (y1_var[msk]/y1[msk]**2 + y2_var[msk]/y2[msk]**2)

        return o

    def dump(self,outfile=None):

        if not outfile is None:
            f = open(outfile,'w')
        else:
            f = sys.stdout

        for i in range(len(self._x)):
            f.write('%5i %10.5g %10.5g %10.5g %10.5g\n'%(i,self._axis.edges()[i],
                                                         self._axis.edges()[i+1],
                                                         self._counts[i],
                                                         self._var[i]))


    def fit(self,expr,p0):

        import ROOT
        import re

        g = ROOT.TGraphErrors()
        f1 = ROOT.TF1("f1",expr)
#        f1.SetDirectory(0)

        for i in range(len(p0)): f1.SetParameter(i,p0[i])

        npar = len(tuple(re.finditer('\[([\d]+)\]',expr)))
        for i in range(self._axis.nbins()):
            g.SetPoint(i,self._axis.center()[i],self._counts[i])
            g.SetPointError(i,0.0,self._counts[i]*0.1)

        g.Fit("f1","Q")

        p = np.zeros(npar)
        for i in range(npar): p[i] = f1.GetParameter(i)
        return p

    def find_root(self,y,x0=None,x1=None):
        """Solve for the x coordinate at which f(x)-y=0 where f(x) is
        a smooth interpolation of the histogram contents."""

        fn = UnivariateSpline(self._axis.center(),self._counts,k=2,s=0)

        if x0 is None: x0 = self._axis.lo_edge()
        if x1 is None: x1 = self._axis.hi_edge()

        return brentq(lambda t: fn(t) - y,x0,x1)

    def find_max(self,msk=None):

        if msk is None:
            msk = np.empty(self._axis.nbins(),dtype='bool'); msk.fill(True)

        return np.argmax(self._counts[msk])


    def __mul__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, Histogram):
            o._counts *= x._counts
            o._var *= x._counts**2
        else:
            o._counts *= x
            o._var *= x*x

        return o

    def __div__(self,x):

        if isinstance(x, Histogram):
            o = self.divide(x)
        else:
            o = copy.deepcopy(self)
            o._counts /= x
            o._var /= x*x

        return o


    def __add__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, Histogram):
            o._counts += x._counts
            o._var += x._var
        else:
            o._counts += x
            o._var += x

        return o


    def __sub__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, Histogram):
            o._counts -= x._counts
            o._var += x._var
        else:
            o._counts -= x
            o._var += x

        return o

    def _prepare_xaxis(self, rotation=0, alignment='center'):
        """Apply bounds and text labels on x axis."""
#        if self.binlabels is not None:
#            plt.xticks(self._x, self.binlabels,
#                       rotation=rotation, ha=alignment)
        plt.xlim(self._axis.edges()[0], self._axis.edges()[-1])





class Histogram2D(HistogramND):

    default_draw_style = { 'interpolation' : 'nearest' }
    default_style = { 'keep_aspect' : False, 'logz' : False }

    def __init__(self, xaxis, yaxis, label = '__nolabel__', 
                 counts=None, var=None, style=None):

        super(Histogram2D, self).__init__([xaxis,yaxis],label,counts,var)

#        if isinstance(xaxis,Axis): self._xaxis = copy.deepcopy(xaxis)
#        else: self._xaxis = Axis(xaxis)
        
#        if isinstance(yaxis,Axis): self._yaxis = copy.deepcopy(yaxis)
#        else: self._yaxis = Axis(yaxis)

        self._xaxis = self._axes[0]
        self._yaxis = self._axes[1]

        self._nbins = self._xaxis.nbins()*self._yaxis.nbins()


#        if not counts is None: self._counts = counts
#        else: self._counts = np.zeros(shape=(self._xaxis.nbins(),
#                                             self._yaxis.nbins()))
        
#        if not var is None: self._var = var
#        else: self._var = np.zeros(shape=(self._xaxis.nbins(),
#                                          self._yaxis.nbins()))

        self._style = dict(Histogram2D.default_style.items() +
                           Histogram2D.default_draw_style.items())

        if not style is None: update_dict(self._style,style)
        self._style['label'] = label


    @staticmethod
    def createFromTree(t,varname,cut,hdef=None,fraction=0.0,
                       label = '__nolabel__'):

        from ROOT import gDirectory

        draw = '%s>>hist'%(varname)

        if not hdef is None:
            draw += '(%i,%f,%f,%i,%f,%f)'%(hdef[0][0],hdef[0][1],hdef[0][2],
                                           hdef[1][0],hdef[1][1],hdef[1][2])

        nevent = t.GetEntries()
        first_entry = int(nevent*fraction)

        ncut = t.Draw(draw,cut,'goff',nevent,first_entry)

        h = gDirectory.Get('hist')
        h.SetDirectory(0)
        return Histogram2D.createFromTH2(h)

    @staticmethod
    def createFromTH2(hist,label = '__nolabel__'):
        nx = hist.GetNbinsX()
        ny = hist.GetNbinsY()

        xmin = hist.GetXaxis().GetBinLowEdge(1)
        xmax = hist.GetXaxis().GetBinLowEdge(nx+1)

        ymin = hist.GetYaxis().GetBinLowEdge(1)
        ymax = hist.GetYaxis().GetBinLowEdge(ny+1)

        xaxis = Axis.create(xmin,xmax,nx)
        yaxis = Axis.create(ymin,ymax,ny)

        counts = np.zeros(shape=(nx,ny))
        var = np.zeros(shape=(nx,ny))

        for ix in range(1,nx+1):
            for iy in range(1,ny+1):
                counts[ix-1][iy-1] = hist.GetBinContent(ix,iy)
                var[ix-1][iy-1] = hist.GetBinError(ix,iy)**2

        h = Histogram2D(xaxis,yaxis,label,counts=counts,var=var)

        return h

    def label(self):
        return self._style['label']
    
    def update_style(self,style):
        update_dict(self._style,style)

    def nbins(self,idim=None):
        """Return the number of bins in this histogram."""
        if idim is None: return self._nbins
        elif idim == 0: return self.xaxis().nbins()
        elif idim == 1: return self.yaxis().nbins()
        else: return 0

    def xaxis(self):
        return self._xaxis

    def yaxis(self):
        return self._yaxis

    def counts(self,ix=None,iy=None):

        if ix is None: return self._counts
        elif iy is None:
            (ix,iy) = np.unravel_index(ix,self._counts.shape)

        return self._counts[ix,iy]

    def center(self,ix,iy):
        return [self._xaxis.center()[ix],self._yaxis.center()[iy]]

    def xedges(self):
        """Return array of bin edges."""
        return self._xaxis.edges()

    def yedges(self):
        """Return array of bin edges."""
        return self._yaxis.edges()

    def lo_edge(self,ix,iy):
        return (self._xaxis.edges()[ix],self._yaxis.edges()[iy])

    def hi_edge(self,ix,iy):
        return (self._xaxis.edges()[ix+1],self._yaxis.edges()[iy+1])

    def maxIndex(self,ix_range=None,iy_range=None):
        """Return x,y indices of maximum histogram element."""

        if ix_range is None: ix_range = [0,self._xaxis.nbins()+1]
        elif len(ix_range) == 1: ix_range = [ix_range[0],self._xaxis.nbins()+1]

        if iy_range is None: iy_range = [0,self._yaxis.nbins()+1]
        elif len(iy_range) == 1: iy_range = [iy_range[0],self._yaxis.nbins()+1]

        a = np.argmax(self._counts[ix_range[0]:ix_range[1],
                                   iy_range[0]:iy_range[1]])

        cv = self._counts[ix_range[0]:ix_range[1],iy_range[0]:iy_range[1]]
        ixy = np.unravel_index(a,cv.shape)
        return (ixy[0]+ix_range[0],ixy[1]+iy_range[0])

    def sliceByIndex(self,ibin,iaxis=0):
        """Return a cut of the 2D histogram at the given bin index."""

        return self.marginalize(iaxis,bin_range=[ibin,ibin+1])

    def sliceByValue(self,value,iaxis=0):

        if iaxis==0: bin = self._xaxis.valToBin(value)
        else: bin = self._yaxis.valToBin(value)
        return self.sliceByIndex(bin,iaxis)

    def cut(self,iaxis=0,ibin=0):

        h = None

        if iaxis == 0:
            h = Histogram(self._yaxis,
                          counts=self._counts[ibin,:],
                          var=self._var[ibin,:])
        else:
            h = Histogram(self._xaxis,
                          counts=self._counts[:,ibin],
                          var=self._var[:,ibin])

        return h

    def interpolate(self,x,y):
        from util import interpolate2d
        return interpolate2d(self._xaxis.edges(),
                             self._yaxis.edges(),self._counts,x,y)

    def integrate(self,iaxis=1,bin_range=None):
        if iaxis == 1:

            if bin_range is None: bin_range = [0,self._yaxis.nbins()]

            h = Histogram(self._xaxis.edges())
            for iy in range(bin_range[0],bin_range[1]):
                h._counts[:] += self._counts[:,iy]*self._ywidth[iy]
                h._var[:] += self._var[:,iy]*self._ywidth[iy]**2

            return h


    def marginalize(self,iaxis=1,bin_range=None):
        """Return 1D histogram marginalized over x or y dimension."""
        if iaxis == 1:

            if bin_range is None: bin_range = [0,self._yaxis.nbins()]

            h = Histogram(self._xaxis.edges())
            for iy in range(bin_range[0],bin_range[1]):
                h._counts[:] += self._counts[:,iy]
                h._var[:] += self._var[:,iy]

            return h
        else:

            if bin_range is None: bin_range = [0,self._xaxis.nbins()]

            h = Histogram(self._yaxis.edges())
            for ix in range(bin_range[0],bin_range[1]):
                h._counts[:] += self._counts[ix,:]
                h._var[:] += self._var[ix,:]

            return h

    def mean(self,iaxis=0,**kwargs):

        hq = Histogram(self._xaxis.edges())

        for i in range(self.nbins(0)):
            h = self.sliceByIndex(i,iaxis)

            x = h.axis().center()

            mean = np.sum(h.counts()*x)/np.sum(h.counts())
            mean_var = mean**2*(np.sum(h.var()*x**2)/np.sum(h.counts()*x)**2 +
                                np.sum(h.var())/np.sum(h.counts())**2)

            hq._counts[i] = mean
            hq._var[i] = mean_var

        return hq

    def quantile(self,iaxis=0,fraction=0.68,**kwargs):

        import stats

        hq = Histogram(self._xaxis.edges())

        for i in range(self.nbins(0)):
            h = self.sliceByIndex(i,iaxis)

            q,qerr = stats.HistQuantile(h).eval(fraction,**kwargs)

            hq._counts[i] = q
            hq._var[i] = qerr**2

        return hq


    def set(self,ix,iy,w,var=None):
        self._counts[ix,iy] = w
        if not var is None: self._var[ix,iy] = var

    def fill(self,x,y,w=1,var=None):

        x = np.array(x,ndmin=1)
        y = np.array(y,ndmin=1)
        w = np.array(w,ndmin=0)

        if var is None: var = w**2

        bins = [self._xaxis.edges(),self._yaxis.edges()]

        if w.ndim == 1:
            c1 = np.histogram2d(x,y,bins=bins,weights=w)[0]
            c2 = np.histogram2d(x,y,bins=bins,weights=var)[0]

            self._counts += c1
            self._var += c2
        else:
            c = np.histogram2d(x,y,bins=bins)[0]

            self._counts += w*c
            self._var += var*c


    def __div__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, Histogram2D):

            msk = (self._counts == 0) | (x._counts == 0)

            o._counts[msk] = 0.0
            o._var[msk] = 0.0

            o._counts[msk == False] = \
                self._counts[msk == False] / x._counts[msk == False]
#            o._var[i] = (y1[i] / y2[i])**2
#            o._var[i] *= (y1_var[i]/y1[i]**2 + y2_var[i]/y2[i]**2)
        else:
            o._counts /= x
            o._var /= x**2

        return o

    def __mul__(self,x):

        o = copy.deepcopy(self)

        if isinstance(x, Histogram2D):
            o._counts = self._counts*x._counts
            o._var = o._counts*np.sqrt(self._var/self._counts +
                                       x._var/x._counts)
        else:
            o._counts *= x
            o._var *= x**2

        return o


    def contour(self,ax=None,**kwargs):

#        levels = [2.,4.,6.,8.,10.]

        style = copy.deepcopy(self._style)
        style.update(kwargs)

        if style['logz']: norm = LogNorm()
        else: norm = Normalize()

        clear_dict_by_keys(style,Histogram2D.default_draw_style.keys(),False)

        cs = plt.contour(self._xaxis.center(),self._yaxis.center(),
                         self._counts.T,
                         origin='lower',**style)
#        plt.clabel(cs, fontsize=9, inline=1)

        return cs

    def smooth(self,sigma):

        from scipy import ndimage

        sigma_bins = sigma/(self._xaxis.edges()[1]-self._xaxis.edges()[0])

        counts = ndimage.gaussian_filter(self._counts, sigma=sigma_bins)
        var = ndimage.gaussian_filter(self._var, sigma=sigma_bins)

        return Histogram2D(self._xaxis,self._yaxis,counts=counts,var=var)


    def plot(self,ax=None,**kwargs):

        style = copy.deepcopy(self._style)
        style.update(kwargs)

        dx = self._xaxis.hi_edge() - self._xaxis.lo_edge()
        dy = self._yaxis.hi_edge() - self._yaxis.lo_edge()

        aspect_ratio = 1
        if not style['keep_aspect']: aspect_ratio=dx/dy

        if ax is None: ax = plt.gca()

        from matplotlib.colors import NoNorm, LogNorm, Normalize

        if style['logz']: norm = LogNorm()
        else: norm = Normalize()

        clear_dict_by_keys(style,Histogram2D.default_draw_style.keys(),False)

        return ax.imshow(self._counts.transpose(),
                         origin='lower',
                         aspect=aspect_ratio,norm=norm,
                         extent=[self._xaxis.lo_edge(), self._xaxis.hi_edge(),
                                 self._yaxis.lo_edge(), self._yaxis.hi_edge()],
                         **style)

#                   vmin=vmin,vmax=vmax)

def get_vector(chain,var,cut='',nentries=0,first_entry=0):

    chain.SetEstimate(chain.GetEntries())
    ncut = chain.Draw('%s'%(var),cut,'goff',nentries,first_entry)
    return copy.deepcopy(np.frombuffer(chain.GetV1(),
                                       count=ncut,dtype='double'))





if __name__ == '__main__':

    fig = plt.figure()

    hnd = HistogramND([np.linspace(0,1,10),
                       np.linspace(0,1,10)])




    h1d = Histogram([0,10],10)


    h1d.fill(3.5,5)
    h1d.fill(4.5,3)
    h1d.fill(1.5,5)
    h1d.fill(8.5,1)
    h1d.fill(9.5,1)


    print h1d.axis().edges()

    for x in h1d.iterbins():
        print x.center(), x.counts()


    h1d.rebin([4,4,2])

    print h1d.axis().edges()
        
