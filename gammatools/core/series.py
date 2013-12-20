#!/usr/bin/env python

"""
@file  series.py

@brief Python class representing series data (arrays of x/y pairs)."

@author Matthew Wood <mdwood@slac.stanford.edu>
"""

import copy
import numpy as np
import matplotlib.pyplot as plt
from util import *

class Series(object):

    default_style = { 'marker' : None,
                      'color' : None,
                      'markersize' : None,
                      'markerfacecolor' : None,
                      'markeredgecolor' : None,
                      'linestyle' : None,
                      'linewidth' : 1,
                      'label' : None,
                      'msk' : None }


    def __init__(self,x,y,yerr=None,style=None):
        self._x = np.array(x,copy=True)
        self._y = np.array(y,copy=True)
        if not yerr is None: self._yerr = np.array(yerr,copy=True)
        else: self._yerr = yerr

        self._style = copy.deepcopy(Series.default_style)
        if not style is None: update_dict(self._style,style)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def yerr(self):
        return self._yerr

    def label(self):
        return self._style['label']

    def style(self):
        return self._style

    def update_style(self,style):
        update_dict(self._style,style)

    def plot(self,ax=None,**kwargs):

        if ax is None: ax = plt.gca()

        style = copy.deepcopy(self._style)

        update_dict(style,kwargs)
        clear_dict_by_vals(style,None)
        ax.errorbar(self._x,self._y,self._yerr,**style)

    def mask(self,msk):

        o = copy.deepcopy(self)
        o._x = self._x[msk]
        o._y = self._y[msk]
        if not o._yerr is None:
            o._yerr = self._yerr[msk]

        return o
        
    def __div__(self,x):

        o = copy.deepcopy(self)
        o._y /= x
        if not o._yerr is None: o._yerr /= x
        return o
        

if __name__ == '__main__':

    fig = plt.figure()


    x0 = np.linspace(0,2*np.pi,100.)
    y0 = 2. + np.sin(x0)
    y1 = 2. + 0.5*np.sin(x0+np.pi/4.)

    
    s = Series(x0,y0)

    s.plot(marker='o',color='b',markerfacecolor='w',markeredgecolor='b')

    plt.show()