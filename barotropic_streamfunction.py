from netCDF4 import Dataset
from numpy import *
from matplotlib.pyplot import *
from fesom_grid import *
from unrotate_vector import *
from in_triangle import *

def barotropic_streamfunction (mesh_path, file_path, tstep, save=False, fig_name=None):

    # Bounds on regular grid
    lon_min = -180
    lon_max = 180
    lat_min = -90
    lat_max = -30
    # Number of points on regular grid
    num_lon = 1000
    num_lat = 1000
    # Radius of the Earth in metres
    r = 6.371e6
    # Degrees to radians coversion factor
    deg2rad = pi/180.0

    print 'Building mesh'
    elements = fesom_grid(mesh_path, circumpolar=False, cross_180=True)
    # Read number of 2D nodes
    f = open(mesh_path + 'nod2d.out', 'r')
    n2d = int(f.readline())
    f.close()
    # Read (rotated) lon, lat, and depth, at each 3D node
    f = open(mesh_path + 'nod3d.out', 'r')
    f.readline()
    rlon = []
    rlat = []
    node_depth = []
    for line in f:
        tmp = line.split()
        lon_tmp = float(tmp[1])
        lat_tmp = float(tmp[2])
        node_depth_tmp = -1*float(tmp[3])
        if lon_tmp < -180:
            lon_tmp += 360
        elif lon_tmp > 180:
            lon_tmp -= 360
        rlon.append(lon_tmp)
        rlat.append(lat_tmp)
        node_depth.append(node_depth_tmp)
    f.close()
    rlon = array(rlon)
    rlat = array(rlat)
    node_depth = array(node_depth)
    # Read lists of which nodes are directly below which
    f = open(mesh_path + 'aux3d.out', 'r')
    max_num_layers = int(f.readline())
    node_columns = zeros([n2d, max_num_layers])
    for n in range(n2d):
        for k in range(max_num_layers):
            node_columns[n,k] = int(f.readline())
    node_columns = node_columns.astype(int)
    f.close()
    # Set up regular grid
    # Start with boundaries
    lon_reg_edges = linspace(lon_min, lon_max, num_lon+1)
    lat_reg_edges = linspace(lat_min, lat_max, num_lat+1)
    # Now get centres
    lon_reg = 0.5*(lon_reg_edges[:-1] + lon_reg_edges[1:])
    lat_reg = 0.5*(lat_reg_edges[:-1] + lat_reg_edges[1:])
    # Also get differentials in lon-lat space
    dlon = lon_reg_edges[1:] - lon_reg_edges[:-1]
    dlat = lat_reg_edges[1:] - lat_reg_edges[:-1]
    # Make 2D versions
    lon_reg_2d, lat_reg_2d = meshgrid(lon_reg, lat_reg)
    dlon_2d, dlat_2d = meshgrid(dlon, dlat)
    # Calculate differentials in Cartesian space
    dx = r*cos(lat_reg_2d*deg2rad)*dlon_2d*deg2rad
    dy = r*dlat_2d*deg2rad

    print 'Reading data'
    # Read 3D rotated u and v
    id = Dataset(file_path, 'r')
    ur = id.variables['u'][tstep-1,:]
    vr = id.variables['v'][tstep-1,:]
    id.close()
    # Unrotate
    u, v = unrotate_vector(rlon, rlat, ur, vr)
    # Vertically integrate u*dz
    int_udz = zeros(n2d)
    # Loop over nodes
    for n in range(n2d):
        # Loop over depth
        for k in range(max_num_layers-1):
            if node_columns[n,k+1] == -999:
                # Reached the bottom
                break
            # Trapezoidal rule
            top_id = node_columns[n,k]
            bot_id = node_columns[n,k+1]
            dz = node_depth[bot_id-1] - node_depth[top_id-1]
            int_udz[n] += 0.5*(u[top_id-1] + u[bot_id-1])*dz

    print 'Interpolating to regular grid'
    int_udz_reg = zeros([num_lat, num_lon])
    # For each element, check if a point on the regular lat-lon grid lies
    # within. If so, do barycentric interpolation to that point.
    for elm in elements:
        # Check if we are within domain of regular grid
        if amin(elm.lat) > lat_max:
            continue
        # Find largest regular longitude value west of Element
        tmp = nonzero(lon_reg > amin(elm.lon))[0]
        if len(tmp) == 0:
            # Element crosses the western boundary
            iW = 0
        else:
            iW = tmp[0] - 1
        # Find smallest regular longitude value east of Element
        tmp = nonzero(lon_reg > amax(elm.lon))[0]
        if len(tmp) == 0:
            # Element crosses the eastern boundary
            iE = num_lon
        else:
            iE = tmp[0]
        # Find largest regular latitude value south of Element
        tmp = nonzero(lat_reg > amin(elm.lat))[0]
        if len(tmp) == 0:
            # Element crosses the southern boundary
            jS = 0
        else:
            jS = tmp[0] - 1
        # Find smallest regular latitude value north of Element
        tmp = nonzero(lat_reg > amax(elm.lat))[0]
        if len(tmp) == 0:
            # Element crosses the northern boundary
            jN = num_lat
        else:
            jN = tmp[0]
        for i in range(iW+1,iE):
            for j in range(jS+1,jN):
                # There is a chance that the regular gridpoint at (i,j)
                # lies within this element
                lon0 = lon_reg[i]
                lat0 = lat_reg[j]
                if in_triangle(elm, lon0, lat0):
                    # Get area of entire triangle
                    area = triangle_area(elm.lon, elm.lat)
                    # Get area of each sub-triangle formed by
                    # (lon0, lat0)
                    area0 = triangle_area([lon0, elm.lon[1], elm.lon[2]], [lat0, elm.lat[1], elm.lat[2]])
                    area1 = triangle_area([lon0, elm.lon[0], elm.lon[2]], [lat0, elm.lat[0], elm.lat[2]])
                    area2 = triangle_area([lon0, elm.lon[0], elm.lon[1]], [lat0, elm.lat[0], elm.lat[1]])
                    # Find fractional area of each
                    cff = [area0/area, area1/area, area2/area]
                    # Find value of int_udz at each Node
                    vals = []
                    for n in range(3):
                        vals.append(int_udz[elm.nodes[n].id])
                    # Barycentric interpolation to lon0, lat0
                    int_udz_reg[j,i] = sum(array(cff)*array(vals))

    # Indefinite integral from south to north of udz*dy, convert to Sv
    strf = cumsum(int_udz_reg*dy, axis=0)*1e-6
    # Apply land mask: wherever interpolated field was identically zero
    strf = ma.masked_where(int_udz_reg==0, strf)

    print 'Plotting'
    fig = figure(figsize=(10,6))
    ax = fig.add_subplot(1,1,1)
    pcolor(lon_reg, lat_reg, strf, cmap='jet')
    xlabel('Longitude')
    ylabel('Latitude')
    xlim([-180, 180])
    ylim([-90, -30])
    colorbar()
    title('Barotropic streamfunction (Sv)', fontsize=20)

    if save:
        fig.savefig(fig_name)
    else:
        fig.show()


# Command-line interface
if __name__ == "__main__":

    mesh_path = raw_input("Path to FESOM mesh directory: ")
    file_path = raw_input("Path to FESOM output file containing u and v: ")
    tstep = int(raw_input("Time index to plot (starting at 1): "))
    action = raw_input("Save figure (s) or display on screen (d)? ")
    if action == 's':
        save = True
        fig_name = raw_input("Path to filename for figure: ")
    elif action == 'd':
        save = False
        fig_name = None
    barotropic_streamfunction(mesh_path, file_path, tstep, save, fig_name)
    
