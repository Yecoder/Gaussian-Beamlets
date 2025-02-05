%% Controlling the Differential Ray Trace Algorithm
% Author: Jaren Ashcraft
% To be replaced by a Python script when the API becomes accessible
%
% This is a script that traces rays to compute the differential ray
% traceing matrix (ABCD) of each surface in an Zemax OpticStudio 
% optical system. 
% 
% All of the math will be in here for the sake of having an isolated
% product, but the idea is to have it in python with the GBD module - we
% just need to configure the ZOS-API in python which has been proven to be
% a bit tricky. Because of this I won't be fleshing out the best product I
% can, just getting the code to work as quickly as possible.

clear all % just for my sanity
%% User Inputs
pth = 'C:/Users/UASAL-OPTICS/Desktop/Gaussian-Beamlets/'; 
fn_ini = 'Hubble_Test';
fov_to_trace_x = 0; % degrees
fov_to_trace_y = 0; % degrees
fov_max = 0.08; % degrees
pupil_max = 2.4/2;
nrays = 113; % number of rays across the pupil
dz = 1e-4; % separation of parabasal rays
surface = [1,10];

% I'd like this to work for a Cassegrain Objective
% 0 for refraction, 1 for propagation
system = [2];
nsur = length(surface);

%% Some filename translation
fn = strcat(pth,fn_ini);
fnex = strcat(fn,'.zmx');

%% Set up the Differential Vectors & Trace Rays

% Divide by maximum to normalize the coordinates - we are tracing in
% Normalized Unpolarized mode
dPx = [0,1,0,0,0]*dz/pupil_max;
dPy = [0,0,1,0,0]*dz/pupil_max;
dHx = [0,0,0,1,0]*dz;
dHy = [0,0,0,0,1]*dz;

hx = (fov_to_trace_x + dHx)/fov_max;
hy = (fov_to_trace_y + dHy)/fov_max;

xdat = {};
ydat = {};
zdat = {};
ldat = {};
mdat = {};
ndat = {};
ABCD = {}; % will be a cell of cells because I'm bad at this


[ABCD,Px,Py] = trace_system(surface,nrays,hx,hy,dPx,dPy,fnex);
displayABCD(ABCD,Px,Py)
% 
% for abc = 1:nsur
%     
%     if system(abc) == 1
%         
%         ABCD{end+1} = trace_distance(surface(abc),nrays,hx,hy,dPx,dPy,fnex);
%         
%     elseif system(abc) == 0
%         
%         ABCD{end+1} = trace_refraction(surface(abc),nrays,hx,hy,dPx,dPy,fnex);
%         
%     else
%         disp('Tracing Total System')
%         ABCD = trace_system(surface,nrays,hx,hy,dPx,dPy,fnex);
%         
%     end
%     
% end

% for ijk = 1:5
%     
%     hx = (fov_to_trace_x + dHx(ijk))/fov_max;
%     hy = (fov_to_trace_y + dHy(ijk))/fov_max;
%     [xData,yData,zData,lData,mData,nData,l2Data,m2Data,n2Data,n1,n2 ] = MATLAB_BatchRayTrace_ReadRayData(...
%         surface,nrays,hx,hy,dPx(ijk),dPy(ijk),fnex);
%     
%     xData = xData';
%     yData = yData';
%     zData = zData';
% 
%     lData = lData';
%     mData = mData';
%     nData = nData';
% 
%     l2Data = l2Data';
%     m2Data = m2Data';
%     n2Data = n2Data';
%     % Create a table with the data and variable names
%     T = table(xData,yData,zData,lData,mData,nData,l2Data,m2Data,n2Data);%,...
%     %     'ColumnNames',...
%     %     { 'xData','yData','zData','lData','mData','nData','l2Data','m2Data','n2Data','n1','n2'} );
% 
%     % Write data to text file
%     fn = 'C:/Users/UASAL-OPTICS/Desktop/gbd-data/';
%     fn = strcat(fn,fn_ini);
%     if strcmp(where,'input')==1
%         
%         full_filename = strcat(fn,sprintf('_ray%d_data_in.txt',ijk-1));
%         
%     elseif strcmp(where,'output')==1
%         
%         full_filename = strcat(fn,sprintf('_ray%d_data.txt',ijk-1));
%         
%     end
%     writetable(T, full_filename)
%     
%     
%     
% end

function displayABCD(ABCD,x,y)

plotbox = zeros(4,4,length(ABCD));
sz = 5;
pcount = 0;
titstring = {'Axx','Axy','Bxx','Bxy',...
             'Ayx','Ayy','Byx','Byy',...
             'Cxx','Cxy','Dxx','Dxy',...
             'Cyx','Cyy','Dyx','Dyy'};
    
    % reformat the arrays
    for ijk = 1:length(ABCD)
        plotbox(:,:,ijk) = ABCD{ijk};
    end
    
    % please don't judge my ability to matlab by the following code
    figure(1)
    hold on
    
        for lmn = 1:4
            for opq = 1:4
                pcount = pcount + 1;
                subplot(4,4,pcount)
                hold on
                    title(titstring{pcount})
                    % squeeze() allegedly removes unit dimension axes
                    scatter(x,y,sz,squeeze(plotbox(lmn,opq,:)),'filled')
                    colorbar
                hold off
                
            end
        end
    
    hold off



end

