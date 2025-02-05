# Package Import Section
import numpy as np
import matplotlib.pyplot as plt
import numexpr as ne
import timeit
import astropy.units as u
from scipy.special import erfc
from numba import jit
from numpy.fft import fft


# Determine sampling scheme experimental (fiib = fibbonacci spacing, else uniform cartesian)
samplescheme = 'fib'

# Creating an Optical System Class To propagate rays
class GaubletOpticalSystem:

    def __init__(self,
                 epd,
                 npix,
                 dimd,
                 wavelength):

        basesys = np.array([[1.0,0,0,0],
                            [0,1.0,0,0],
                            [0,0,1.0,0],
                            [0,0,0,1.0]])
        self.system = basesys
        self.epd = epd
        self.npix = npix
        self.dimd = dimd

        # THIS BLOCK IS HARD-CODED, CHANGE FOR FINAL VERSION ##################################################

        # Beamlet Parameters
        self.wl = wavelength# beamlet wavelength
        OF = 2 # Overlap Factor
        wo = 30000.0*self.wl # beamlet waist
        zr = np.pi*wo**2.0/self.wl

        

        if samplescheme == 'fib':

          # Create List of Positions (X,Y) in a Fibbonacci Sampled Spiral Circular Aperture
          self.N = np.int(np.round(np.pi*((self.epd/2.0)*OF/(wo))*9.0)) # EXPERIMENTAL
          print('numbeamlets = ',self.N)
          c = np.array([0,0]) # XY offset from a spiral
          R = (self.epd/2)*np.sqrt(np.linspace(1/2,self.N-1/2,self.N))/np.sqrt(self.N-1/2)
          T = 4/(1+np.sqrt(5))*np.pi*np.linspace(1,self.N,self.N);
          X = c[0] +R*np.cos(T)
          Y = c[1] +R*np.sin(T)

        else:
          # grid samplings

          # number of beamlets across grid
          self.N = int(round(self.epd*OF/(2*wo)))
          print('numbeamlets across grid = ',self.N)

          # Define lists of XY coordinate pairs for square grid
          x = np.linspace(-self.epd/2,self.epd/2,self.N)
          y = np.linspace(-self.epd/2,self.epd/2,self.N)
          x,y = np.meshgrid(x,y)
          X = np.concatenate(x).flatten('F')
          Y = np.concatenate(y).flatten('F')
          self.N = self.N**2
          print('total numbeamlets = ',self.N)

        # THIS BLOCK IS HARD-CODED, CHANGE FOR FINAL VERSION ##################################################


        # Define a Q Matrix - diagonal zero for nonastigmatic, nonrotated case
        qxx = 1.0/(1j*zr)
        qxy = 0.0
        qyx = 0.0
        qyy = 1.0/(1j*zr)
        self.Q = np.array([[qxx,qxy],
                            [qyx,qyy]],dtype='complex') # Defines the matrix of inverse q parameters

        # Create the Base Rays to track GauBlet position
        self.baserays = np.array([X,
                                  Y,
                                  0.0*X,
                                  0.0*Y]) # slopes are all 0 for the base ray of a plane wavefront

    def add_optic(self,efl):

        # Focusing matrix
        optic = np.array([[1.0,0.0,0.0,0.0],
                          [0.0,1.0,0.0,0.0],
                          [-1.0/float(efl),0.0,1.0,0.0],
                          [0.0,-1.0/float(efl),0.0,1.0]])

        # multiply optic by system matrix
        self.system = np.matmul(optic,self.system)

    def add_distance(self,distance,index):

        # Propagation matrix
        propg = np.array([[1.0,0.0,float(distance)/float(index),0.0],
                          [0.0,1.0,0.0,float(distance)/float(index)],
                          [0.0,0.0,1.0,0.0],
                          [0.0,0.0,0.0,1.0]])

        # multiply propagation by system matrix
        self.system = np.matmul(propg,self.system)

    def propagate(self):

        # Propagate the base rays by the system
        prop = np.matmul(self.system,self.baserays)



        # Optical system sub-matrices
        A = self.system[0:2,0:2]
        B = self.system[0:2,2:4]
        C = self.system[2:4,0:2]
        D = self.system[2:4,2:4]

        # Propagate the Q matrix
        Qprop_n = (C + np.matmul(D,self.Q))
        Qprop_d = np.linalg.inv(A+np.matmul(B,self.Q))
        Qprop   = np.matmul(Qprop_n,Qprop_d)
        self.P_pram = np.matmul(np.linalg.inv(np.matmul(C,np.linalg.inv(self.Q))+D),self.baserays[0:2])

        return Qprop,prop

    def add_aperture(self,shape,radi):

      # Generate mask opacity list
      if shape == 'lyot':
        print('generating lyot stop')



      elif shape == 'fpm':
        print('generating focal plane mask')

      # assumes common beam waist radius
      waist = self.Q


class GaubletWavefront:

    def __init__(self,
                 wavelength,
                 numbeamlets,
                 npix,
                 dimension,
                 proprays,
                 baserays,
                 Qorig,
                 Qprop,
                 system,
                 P_pram):

        self.wavelength = wavelength
        self.numbeamlets = numbeamlets
        self.npix = npix
        self.dimension = dimension
        self.proprays = proprays
        self.baserays = baserays
        self.Q = Qorig
        self.Qprop = Qprop
        self.system = system
        u = np.linspace(-self.dimension/2,self.dimension/2,self.npix)
        v = np.linspace(-self.dimension/2,self.dimension/2,self.npix)
        self.u,self.v = np.meshgrid(u,v)
        self.P_pram = P_pram

        # pre-define a datacube to dump the Gaublet phase in
        self.Dphase = np.zeros([npix,npix,self.numbeamlets],dtype='complex')


    def Phasecalc(self): # returns datacube of gaublet phases

        lo = self.system[0,2]
        A  = self.system[0:2,0:2]
        B  = self.system[0:2,2:4]

        orig_matrx = np.linalg.inv(self.Q + np.matmul(np.linalg.inv(A),B))
        cros_matrx = np.linalg.inv(np.matmul(A,self.Q)+B)
        phase = self.Phasecube(self.system,
                               self.numbeamlets,
                               self.dimension,
                               self.npix,
                               self.proprays,
                               self.wavelength,
                               self.Qprop,
                               self.Q,
                               lo,
                               self.Dphase,
                               self.u,
                               self.v,
                               self.P_pram[0,:],
                               self.P_pram[1,:],
                               self.baserays,
                               orig_matrx,
                               cros_matrx)
        phasor = ne.evaluate('exp(phase)')
        Ephase = np.sum(phasor,axis=2)*np.sqrt(np.linalg.det(A+np.matmul(B,self.Q)))

        return Ephase

    @staticmethod
    @jit(nopython=True,parallel=True)
    def Phasecube(system,numbeamlets,dimension,npix,proprays,wavelength,Qprop,Q,lo,Dphase,u,v,P_x,P_y,baserays,orig_matrx,cros_matrx):
        for ind in range(numbeamlets):
            #print(P_x)
            #print(P_y)

            A = system[0:2,0:2]
            B = system[0:2,2:4]
            C = system[2:4,0:2]
            D = system[2:4,2:4]

            uo = u - baserays[0,ind]
            vo = v - baserays[1,ind]

            up = u - proprays[0,ind]
            vp = v - proprays[1,ind]
            #print(up)
            #print(vp)
            guoy_phase = 0#-1j*np.arctan(lo/np.real(Qprop[0,0]))
            tran_phase = (-1j*(np.pi/wavelength))*(Qprop[0,0]*up**2 + (Qprop[1,0] + Qprop[0,1])*up*vp + Qprop[1,1]*vp**2)
            long_phase = (-1j*(2.0*np.pi/wavelength)*lo)
            orig_phase = (-1j*(np.pi/wavelength))*(orig_matrx[0,0]*uo**2 + (orig_matrx[1,0] + orig_matrx[0,1])*uo*vo + orig_matrx[1,1]*vo**2)
            cros_phase = (-1j*(2.0*np.pi/wavelength))*( cros_matrx[0,0]*uo*up + (cros_matrx[1,0] + cros_matrx[0,1])*uo*vp + cros_matrx[1,1]*vo*vp )
            Dphase[:,:,ind] = tran_phase+long_phase+guoy_phase+orig_phase+cros_phase

        return Dphase
        # GPU Computing

    def display(self,field):
        self.dimension = self.dimension*1e6 # convert to microns

        x = np.linspace(-self.dimension/2,self.dimension/2,self.npix)

        self.field = field

        plt.figure(1,figsize=[17,9])
        plt.subplot(1,2,1)
        plt.set_cmap('gray')
        plt.imshow((np.abs(self.field*np.conj(self.field))),
                    extent=[-self.dimension/2,self.dimension/2,-self.dimension/2,self.dimension/2])
        plt.title(' Irradiance')
        plt.xlabel('Detector Dimension [um]')
        plt.ylabel('Detector Dimension [um]')
        plt.colorbar()

        plt.subplot(1,2,2)
        plt.imshow(np.angle((self.field)),
                    extent=[-self.dimension/2,self.dimension/2,-self.dimension/2,self.dimension/2])
        plt.title('Field Phase')
        plt.xlabel('Detector Dimension [um]')
        plt.ylabel('Detector Dimension [um]')
        plt.colorbar()
        plt.show()

        plt.figure(2,figsize=[17,9])
        plt.subplot(121)
        plt.plot(x,np.abs(self.field[int(self.npix/2),:]))
        plt.title('Amplitude Cross Section X')
        plt.xlabel('Detector Dimension [um]')
        plt.ylabel('Amplitude')

        plt.subplot(1,2,2)
        plt.plot(x,np.log(np.abs((self.field[int(self.npix/2),:]))))
        plt.title('Log Amplitude Cross Section X')
        plt.xlabel('Detector Dimension [um]')
        plt.ylabel('Amplitude')
        plt.show()


# Test System - (8*2.2e-6*(5.52085/2.4)**2) is 1 wave of defocus
osys = GaubletOpticalSystem(epd=2.4,npix=512,dimd=2e-5,wavelength=2.2e-6) # 1e-5
osys.add_optic(efl=5.52085)
osys.add_distance(distance=5.52085,index=1)
Qp,prop = osys.propagate()
gwfr = GaubletWavefront(wavelength=osys.wl,numbeamlets=osys.N,npix=osys.npix,dimension=osys.dimd,proprays=prop,baserays=osys.baserays,Qorig=osys.Q,Qprop=Qp,system = osys.system,P_pram=osys.P_pram)
Dfield = gwfr.Phasecalc()
gwfr.display(field=Dfield)