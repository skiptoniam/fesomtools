from netCDF4 import Dataset
from numpy import *
from matplotlib.collections import PatchCollection
from matplotlib.pyplot import *
from matplotlib.cm import *
from patches import *
from monthly_avg import *

# Make a 3x2 plot showing sea ice concentration from low-res FESOM, high-res
# FESOM, and NSIDC observations for February (top) and August (bottom),
# 1992-2005 average.
def aice_minmax_nsidc ():

    # Paths to FESOM mesh and output files
    directory_head = '/short/y99/kaa561/FESOM/'
    mesh_low = directory_head + 'mesh/low_res/'
    mesh_high = directory_head + 'mesh/high_res/'
    expt_dir = ['lowres_spinup/rep3/', 'highres_spinup/rep3/']
    fesom_file = 'avg.ice.mean.nc'  # 1992-2005 climatology for rep3
    # Paths to reconstruct NSIDC files for each month
    nsidc_head1 = '/short/m68/kaa561/nsidc_aice/seaice_conc_monthly_sh_f11_'
    nsidc_head2 = '/short/m68/kaa561/nsidc_aice/seaice_conc_monthly_sh_f13_'
    nsidc_tail = '_v02r00.nc'
    start_year = 1992
    end_year = 2005
    num_years = end_year - start_year + 1
    # Plotting parameters
    circumpolar = True
    mask_cavities = True
    deg2rad = pi/180.0

    # Make plotting patches for low-res FESOM
    elements_low, patches_low = make_patches(mesh_low, circumpolar, mask_cavities)
    # Read monthly averages for February and August of sea ice concentration
    # at each node
    file_path = directory_head + expt_dir[0] + fesom_file
    feb_lowres = monthly_avg(file_path, 'area', 1)
    aug_lowres = monthly_avg(file_path, 'area', 7)
    # Get values for each element
    feb_lowres_values = []
    aug_lowres_values = []
    for elm in elements_low:
        # Mask ice shelf cavities
        if not elm.cavity:
            # Average over 3 nodes making up this element
            feb_lowres_values.append(mean([feb_lowres[elm.nodes[0].id], feb_lowres[elm.nodes[1].id], feb_lowres[elm.nodes[2].id]]))
            aug_lowres_values.append(mean([aug_lowres[elm.nodes[0].id], aug_lowres[elm.nodes[1].id], aug_lowres[elm.nodes[2].id]]))

    # Repeat for high-res FESOM
    elements_high, patches_high = make_patches(mesh_high, circumpolar, mask_cavities)
    file_path = directory_head + expt_dir[1] + fesom_file
    feb_highres = monthly_avg(file_path, 'area', 1)
    aug_highres = monthly_avg(file_path, 'area', 7)
    feb_highres_values = []
    aug_highres_values = []
    for elm in elements_high:
        if not elm.cavity:
            feb_highres_values.append(mean([feb_highres[elm.nodes[0].id], feb_highres[elm.nodes[1].id], feb_highres[elm.nodes[2].id]]))
            aug_highres_values.append(mean([aug_highres[elm.nodes[0].id], aug_highres[elm.nodes[1].id], aug_highres[elm.nodes[2].id]]))

    # Read NSIDC grid
    id = Dataset(nsidc_head1 + '199201' + nsidc_tail, 'r')
    nsidc_lon = id.variables['longitude'][:,:]
    nsidc_lat = id.variables['latitude'][:,:]
    id.close()

    # Read Feburary and August NSIDC sea ice concentration for each year
    feb_nsidc = ma.empty([num_years, size(nsidc_lon,0), size(nsidc_lat,1)])
    aug_nsidc = ma.empty([num_years, size(nsidc_lon,0), size(nsidc_lat,1)])
    # Loop over years
    for year in range(start_year, end_year+1):
        # Reconstruct file paths
        if year < 1996:
            feb_file = nsidc_head1 + str(year) + '02' + nsidc_tail
            aug_file = nsidc_head1 + str(year) + '08' + nsidc_tail
        else:
            feb_file = nsidc_head2 + str(year) + '02' + nsidc_tail
            aug_file = nsidc_head2 + str(year) + '08' + nsidc_tail
        # Read February data and mask
        id = Dataset(feb_file, 'r')
        feb_data_tmp = id.variables['seaice_conc_monthly_cdr'][0,:,:]
        # (This variable is masked but sea ice concentration isn't)
        nsidc_mask = id.variables['stdev_of_seaice_conc_monthly_cdr'][0,:,:]
        id.close()
        # Apply mask
        feb_data = ma.empty(shape(feb_data_tmp))
        feb_data[:,:] = 0.0
        feb_data[~nsidc_mask.mask] = feb_data_tmp[~nsidc_mask.mask]
        feb_data[nsidc_mask.mask] = ma.masked
        # Save result
        feb_nsidc[year-start_year,:,:] = feb_data[:,:]
        # Repeat for August
        id = Dataset(aug_file, 'r')
        aug_data_tmp = id.variables['seaice_conc_monthly_cdr'][0,:,:]
        nsidc_mask = id.variables['stdev_of_seaice_conc_monthly_cdr'][0,:,:]
        id.close()
        aug_data = ma.empty(shape(aug_data_tmp))
        aug_data[:,:] = 0.0
        aug_data[~nsidc_mask.mask] = aug_data_tmp[~nsidc_mask.mask]
        aug_data[nsidc_mask.mask] = ma.masked
        aug_nsidc[year-start_year,:,:] = aug_data[:,:]
    # Average over years
    feb_nsidc = mean(feb_nsidc, axis=0)
    aug_nsidc = mean(aug_nsidc, axis=0)
    # Make sure mask is still there
    feb_nsidc[nsidc_mask.mask] = ma.masked
    aug_nsidc[nsidc_mask.mask] = ma.masked

    # Polar coordinates for plotting
    nsidc_x = -(nsidc_lat+90)*cos(nsidc_lon*deg2rad+pi/2)
    nsidc_y = (nsidc_lat+90)*sin(nsidc_lon*deg2rad+pi/2)
    # Choose boundaries based on extent of NSIDC grid
    bdry1 = amax(nsidc_x[:,0])
    bdry2 = amin(nsidc_x[:,-1])
    bdry3 = amin(nsidc_y[:,0])
    bdry4 = amax(nsidc_y[:,-1])

    # Plot
    fig = figure(figsize=(16,10))
    # Low-res FESOM, February
    ax = fig.add_subplot(2, 3, 1, aspect='equal')
    img = PatchCollection(patches_low, cmap=jet)
    img.set_array(array(feb_lowres_values))
    img.set_clim(vmin=0, vmax=1)
    img.set_edgecolor('face')
    ax.add_collection(img)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    title('Low res', fontsize=24)    
    text(-39, 0, 'February', fontsize=24, ha='right')
    # High-res FESOM, February
    ax = fig.add_subplot(2, 3, 2, aspect='equal')
    img = PatchCollection(patches_high, cmap=jet)
    img.set_array(array(feb_highres_values))
    img.set_clim(vmin=0, vmax=1)
    img.set_edgecolor('face')
    ax.add_collection(img)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    title('High res', fontsize=24)
    # NSDIC, February
    ax = fig.add_subplot(2, 3, 3, aspect='equal')
    img = pcolor(nsidc_x, nsidc_y, feb_nsidc, vmin=0, vmax=1, cmap=jet)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    title('NSIDC', fontsize=24)
    # Low-res FESOM, August
    ax = fig.add_subplot(2, 3, 4, aspect='equal')
    img = PatchCollection(patches_low, cmap=jet)
    img.set_array(array(aug_lowres_values))
    img.set_clim(vmin=0, vmax=1)
    img.set_edgecolor('face')
    ax.add_collection(img)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    text(-39, 0, 'August', fontsize=24, ha='right')
    # High-res FESOM, August
    ax = fig.add_subplot(2, 3, 5, aspect='equal')
    img = PatchCollection(patches_high, cmap=jet)
    img.set_array(array(aug_highres_values))
    img.set_clim(vmin=0, vmax=1)
    img.set_edgecolor('face')
    ax.add_collection(img)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    # NSIDC, August
    ax = fig.add_subplot(2, 3, 6, aspect='equal')
    img = pcolor(nsidc_x, nsidc_y, aug_nsidc, vmin=0, vmax=1, cmap=jet)
    xlim([bdry1, bdry2])
    ylim([bdry3, bdry4])
    axis('off')
    # Add a colourbar at the bottom
    cbaxes = fig.add_axes([0.35, 0.04, 0.3, 0.04])
    cbar = colorbar(img, orientation='horizontal', ticks=arange(0,1+0.25,0.25), cax=cbaxes)
    cbar.ax.tick_params(labelsize=16)
    # Main title
    suptitle('Sea ice concentration (1992-2005)', fontsize=30)
    # Make panels closer together
    subplots_adjust(wspace=0.05, hspace=0.05)

    #fig.show()
    fig.savefig('aice_minmax.png')


# Command-line interface
if __name__ == "__main__":

    aice_minmax_nsidc()
        
