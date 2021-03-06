import numpy as np
import copy

class Vector3D(object):
    
    def __init__(self,x):
        x = np.array(x,ndmin=1,copy=True)
        if x.ndim == 1:
            self._x = x.reshape(3,1)
        else:
            self._x = x

    def x(self):
        """Return cartesian components."""
        return self._x

    def separation(self,v):     
        """Return angular separation between this vector and another vector."""
        costh = np.sum(self._x*v._x,axis=0)        

        costh[costh>1.0] = 1.0
        costh[costh<-1.0]=-1.0

        return np.arccos(costh)
    
    def norm(self):
        return np.sqrt(np.sum(self._x**2,axis=0))

    def theta(self):
        return np.arctan2(np.sqrt(self._x[0]**2 + self._x[1]**2),self._x[2])

    def phi(self):
        return np.arctan2(self._x[1],self._x[0])    

    def lat(self):
        return np.pi/2.-self.theta()

    def lon(self):
        return self.phi()
    
    def normalize(self):
        self._x *= 1./self.norm()

    def rotatex(self,angle):

        angle = np.array(angle,ndmin=1)
        yaxis = Vector3D(angle[np.newaxis,:]*np.array([1.,0.,0.]).reshape(3,1))
        self.rotate(yaxis)

    def rotatey(self,angle):

        angle = np.array(angle,ndmin=1)
        yaxis = Vector3D(angle[np.newaxis,:]*np.array([0.,1.,0.]).reshape(3,1))
        self.rotate(yaxis)

    def rotatez(self,angle):

        angle = np.array(angle,ndmin=1)        
        zaxis = Vector3D(angle[np.newaxis,:]*np.array([0.,0.,1.]).reshape(3,1))
        self.rotate(zaxis)
        
    def rotate(self,axis):
        """Perform a rotation on this vector with respect to an
        arbitrary axis.  The angle of rotation is given by the
        magnitude of the axis vector."""

        angle = axis.norm()
        tmp = np.zeros(self._x.shape) + axis._x
        eaxis = Vector3D(tmp)

        inverse_angle = np.zeros(len(angle))
        inverse_angle[angle>0] = 1./angle[angle>0]

        eaxis._x *= inverse_angle
        par = np.sum(self._x*eaxis._x,axis=0)
        
        paxis = Vector3D(copy.copy(self._x))
        paxis._x -= par*eaxis._x

        cp = eaxis.cross(paxis)
        
        self._x = par*eaxis._x + np.cos(angle)*paxis._x + np.sin(angle)*cp._x
        
    def dot(self,v):

        return np.sum(self._x*v.x(),axis=0)

    def cross(self,axis):
        x = np.zeros(self._x.shape)
        
        x[0] = self._x[1]*axis._x[2] - self._x[2]*axis._x[1]
        x[1] = self._x[2]*axis._x[0] - self._x[0]*axis._x[2]
        x[2] = self._x[0]*axis._x[1] - self._x[1]*axis._x[0]
        return Vector3D(x)

    def project(self,v):
        
        return self*v

    def project2d(self,v):
        
        vp = Vector3D(copy.copy(self._x))

        vp.rotatez(-v.phi())
        vp.rotatey(-v.theta())
        
        return vp
    
    @staticmethod
    def createLatLon(lat,lon):

        return Vector3D.createThetaPhi(np.pi/2.-lat,lon)
        
    @staticmethod
    def createThetaPhi(theta,phi):

        x = np.array([np.sin(theta)*np.cos(phi),
                      np.sin(theta)*np.sin(phi),
                      np.cos(theta)*(1+0.*phi)])

        return Vector3D(x)

    def __getitem__(self, i):
        return Vector3D(self._x[:,i])

    def __mul__(self,v):

        if isinstance(v,Vector3D):
            self._x *= v.x()
        else:
            self._x *= v

        return self

    def __add__(self,v):

        self._x += v.x()
        return self

    def __sub__(self,v):

        self._x -= v.x()
        return self
    
    def __str__(self):
        return self._x.__str__()

if __name__ == '__main__':

    lat = np.array([1.0])#,0.0,-1.0,0.0])
    lon = np.array([0.0])#,1.0, 0.0,-1.0])
    
    v0 = Vector3D.createLatLon(0.0,np.radians(2.0))
    v1 = Vector3D.createLatLon(np.radians(lat),np.radians(lon))

    print 'v0: ', v0
    print 'v1: ', v1
    
    v2 = v1.project2d(v0)

    y = -np.degrees(v2.theta()*np.cos(v2.phi()))
    x = np.degrees(v2.theta()*np.sin(v2.phi()))

    for i in range(4):    
        print '%.3f %.3f'%(x[i], y[i])
