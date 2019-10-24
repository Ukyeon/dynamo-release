import numpy as np
import pandas as pd
import seaborn as sns

import yt

import scipy as sc
from scipy.sparse import issparse
#from licpy.lic import runlic

# moran'I on the velocity genes, etc.

# cellranger data, velocyto, comparison and phase diagram

def cell_wise_velocity(adata, genes, basis='umap', n_columns=1, color=None, cmap=None, s_kwargs_dict={}, layer='X', cell_ind='all', quiver_scale=1, **q_kwargs):
    """Plot the velocity vector of each cell.

    Parameters
    ----------
        adata: :class:`~anndata.AnnData`
            an Annodata object.
        genes: `list`
            The gene names whose gene expression will be faceted.
        basis: `str` (default: `umap`)
            The reduced dimension embedding of cells to visualize.
        n_columns: `int  (default: 1)
            The number of columns of the resulting plot.
        color: `str` or None (default: None)
            Which attribute of cells (column name in the adata.obs) will be used to color cells.
        cmap: `plt.cm` or None (default: None)
            The color map function to use.
        s_kwargs_dict: `dict` (default: {})
            The dictionary of the scatter arguments.
        layer: `str` (default: X)
            Which layer of expression value will be used.
        cell_ind: `str` or `list` (default: all)
            the cell index that will be chosen to draw velocity vectors.
        quiver_scale: scale of quiver plot (default: 1)
            The scale of quiver plot to visualize the velocity vector. If velocity vector is too smaller, decrease the value and vice versa.
        q_kwargs:
            Additional parameters that will be passed to plt.quiver function

    Returns
    -------
        Nothing but a cell wise quiver plot
    """
    import matplotlib.pyplot as plt

    if cmap is None and color is None:
        cmap = plt.cm.RdBu_r

    n_cells, n_genes = adata.shape[0], len(genes)
    # {"alpha": 0.5, "s": 8, "edgecolor": "0.8", "lw": 0.15}
    if cell_ind is "all":
        ix_choice = np.arange(adata.shape[0])
    elif cell_ind is 'random':
        ix_choice = np.random.choice(np.range(adata.shape[0]), size=1000, replace=False)
    elif type(cell_ind) is int:
        ix_choice = np.random.choice(np.range(adata.shape[0]), size=cell_ind, replace=False)
    elif type(cell_ind) is list:
        ix_choice = cell_ind

    quiver_kwargs = {"angles": 'xy', "scale_units": 'xy', 'scale': quiver_scale, "minlength": 1.5}
    quiver_kwargs.update(q_kwargs)
    scatter_kwargs = dict(alpha=0.4, s=8, edgecolor=(0, 0, 0, 1), lw=0.15)
    if s_kwargs_dict is not None:
        scatter_kwargs.update(s_kwargs_dict)

    layer_keys = list(adata.layers.keys())
    layer_keys.extend(['X', 'protein'])

    if layer is 'X':
        E_vec = adata[:, adata.var.index.isin(genes)].X.flatten()
    elif layer in adata.layers.keys():
        E_vec = adata[:, adata.var.index.isin(genes)].layers[layer].flatten()
    elif layer is 'protein': # update subset here
        E_vec = adata[:, adata.var.index.isin(genes)].obsm[layer].flatten()
    else:
        raise Exception(f'The {layer} you passed in is not existed in the adata object.')
    if color is not None:
        n_genes, genes = 1, [color]
        E_vec = adata.obs[color].values if color in adata.obs.keys() else np.empty((0, 1))
        if cmap is None:
            # List of RGB triplets
            color_labels = adata.obs[color].unique()
            rgb_values = sns.color_palette("Set2", len(color_labels))

            # Map label to RGB
            color_map = pd.DataFrame(zip(color_labels, rgb_values), index=color_labels)
            cmap = lambda x: color_map.loc[x, 1]

    X = adata.obsm['X_' + basis] if 'X_' + basis in adata.obsm.keys() else None
    V = adata.obsm['velocity_' + basis] if 'velocity_' + basis in adata.obsm.keys() else None
    if X is None:
        raise Exception(f'The {basis} dimension reduction is not performed over your data yet.')
    if V is None:
        raise Exception(f'The {basis}_velocity velocity (or velocity) result does not existed in your data.')
    if 0 in E_vec.shape:
        raise Exception(f'The gene names {genes} (or cell annotation {color}) provided are not existed in your data.')

    n_columns, plot_per_gene = n_columns, 1 # we may also add random velocity results
    nrow, ncol = int(np.ceil(plot_per_gene * n_genes / n_columns)), n_columns
    plt.figure(None, (3*ncol, 3*nrow)) # , dpi=160

    E_vec = E_vec.A if issparse(E_vec) else E_vec
    V = V.A if issparse(V) else V

    df = pd.DataFrame({"x": np.tile(X[:, 0], n_genes), "y": np.tile(X[:, 1], n_genes), "u": np.tile(V[:, 0], n_genes),
                       "v": np.tile(V[:, 1], n_genes), 'gene': np.repeat(np.array(genes), n_cells),
                       "expression": E_vec}, index=range(n_cells * n_genes))

    # the following code is inspired by https://github.com/velocyto-team/velocyto-notebooks/blob/master/python/DentateGyrus.ipynb
    gs = plt.GridSpec(nrow, ncol)
    for i, gn in enumerate(genes):
        ax = plt.subplot(gs[i*plot_per_gene])
        try:
            ix=np.where(adata.var.index == gn)[0][0]
        except:
            continue

        cur_pd = df.loc[df.gene == gn, :]

        E_vec = cur_pd.loc[:, 'expression']

        if type(E_vec[0]) is float:
            limit = np.max(np.abs(np.percentile(E_vec, [1, 99])))  # upper and lowe limit / saturation

            E_vec = E_vec + limit  # that is: tmp_colorandum - (-limit)
            E_vec = E_vec / (2 * limit)  # that is: tmp_colorandum / (limit - (-limit))
            E_vec = np.clip(E_vec, 0, 1)

            ax.scatter(cur_pd.iloc[:, 0], cur_pd.iloc[:, 1], c=cmap(E_vec), **scatter_kwargs)
        else:
            ax.scatter(cur_pd.iloc[:, 0], cur_pd.iloc[:, 1], c=color_map.loc[E_vec, 1].values, **scatter_kwargs)

        ax.quiver(cur_pd.iloc[ix_choice, 0], cur_pd.iloc[ix_choice, 1],
                   cur_pd.iloc[ix_choice, 2], cur_pd.iloc[ix_choice, 3],
                   **quiver_kwargs)
        ax.axis("off")

    plt.show()


def velocity_on_grid(adata, show_stream_plot=False, **kwargs):
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_style('ticks')

    n_cells, n_genes = adata.shape[0], len(genes)

    if cell_ind is "auto":
        ix_choice = np.range(adata.shape[1])
    elif cell_ind is 'random':
        ix_choice = np.random.choice(np.range(adata.shape[1]), size=1000, replace=False)
    elif type(cell_ind) is int:
        ix_choice = np.random.choice(np.range(adata.shape[1]), size=cell_ind, replace=False)
    elif type(cell_ind) is list:
        ix_choice = cell_ind

    quiver_kwargs = {"angles": 'xy', "scale_units": 'xy', 'scale': quiver_scale, "minlength": 1.5}
    scatter_kwargs = dict(c="0.8", alpha=0.4, s=10, edgecolor=(0, 0, 0, 1), lw=0.3)
    scatter_kwargs.update(s_kwargs_dict)

    layer_keys = list(adata.layers.keys())
    layer_keys.extend(['X', 'protein'])

    if layer is 'X':
        E_vec = adata[gene].X
    elif layer in adata.layers.keys():
        E_vec = adata[gene].layers[layer]
    elif layer is 'protein': # update subset here
        E_vec = adata[gene].obsm[layer]
    else:
        raise Exception(f'The {layer} you passed in is not existed in the adata object.')

    X = adata.obsm['X_' + basis] if 'X_' + basis in adata.obsm.keys() else None
    V = adata.layer['velocity_' + vkey] if 'velocity_' + vkey in adata.obsm.layers() else None
    if X is None:
        raise Exception(f'The {basis} dimension reduction is not performed over your data yet.')
    if V is None:
        raise Exception(f'The {vkey} velocity result does not existed in your data.')

    n_columns = 3 # we may also add random velocity results
    nrow, ncol = int(np.ceil(n_columns * n_genes / 6)), n_columns
    plt.figure(None, (n_columns*nrow, n_columns*ncol), dpi=160)

    if issparse(E_vec):
        E_vec = E_vec.A

    df = pd.DataFrame({"x": np.tile(X[:, 0], n_genes), "y": np.tile(X[:, 1], n_genes), "u": np.tile(V[:, 0], n_genes),
                       "v": np.tile(V[:, 1], n_genes), 'gene': np.repeat(np.array(genes), n_cells),
                       "expression": E_vec.flatten()}, index=range(n_cells * n_genes))

    # the following code is inspired by https://github.com/velocyto-team/velocyto-notebooks/blob/master/python/DentateGyrus.ipynb
    gs = plt.GridSpec(nrow, ncol)
    for i, gn in enumerate(genes):
        ax = plt.subplot(gs[i*n_columns])
        try:
            ix=np.where(adata.var.index == gn)[0][0]
        except:
            continue

        cur_pd = df.loc[df.gene == gn, :]

        ax.scatter(cur_pd[:, 0], cur_pd[:, 1], **_scatter_kwargs)

        ax.quiver(cur_pd[ix_choice, 0], cur_pd[ix_choice, 1],
                   cur_pd[ix_choice, 2], cur_pd[ix_choice, 3],
                   scale=quiver_scale, **_quiver_kwargs)
        if show_stream_plot:
            # X, Y, U, V need to be matrix; update this
            ax3.streamplot(X, Y, U, V, color=U, linewidth=2,
                           cmap='autumn')

        ax.axis("off")


def cell_wise_velocity_3d():
    pass

def velocity_on_grid_3d():
    pass

# def velocity(adata, type) # type can be either one of the three, cellwise, velocity on grid, streamline plot.
#	"""
#
#	"""
#


def plot_LIC_gray(tex):
    """GET_P estimates the posterior probability and part of the energy.

    Arguments
    ---------
        Y: 'np.ndarray'
            Original data.
        V: 'np.ndarray'
            Original data.
        sigma2: 'float'
            sigma2 is defined as sum(sum((Y - V)**2)) / (N * D)
        gamma: 'float'
            Percentage of inliers in the samples. This is an inital value for EM iteration, and it is not important.
        a: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.

    Returns
    -------
    P: 'np.ndarray'
        Posterior probability, related to equation 27.
    E: `np.ndarray'
        Energy, related to equation 26.

    """
    import matplotlib.pyplot as plt

    tex = tex[:, ::-1]
    tex = tex.T

    M, N = tex.shape
    texture = np.empty((M, N, 4), np.float32)
    texture[:, :, 0] = tex
    texture[:, :, 1] = tex
    texture[:, :, 2] = tex
    texture[:, :, 3] = 1

#     texture = scipy.ndimage.rotate(texture,-90)
    plt.figure()
    plt.imshow(texture)


def plot_LIC(U_grid, V_grid, method = 'yt', cmap = "viridis", normalize = False, density = 1, lim=(0,1), const_alpha=False, kernellen=100, xlab='Dim 1', ylab='Dim 2', file = None):
    """Visualize vector field with quiver, streamline and line integral convolution (LIC), using velocity estimates on a grid from the associated data.
    A white noise background will be used for texture as default. Adjust the bounds of lim in the range of [0, 1] which applies
    upper and lower bounds to the values of line integral convolution and enhance the visibility of plots. When const_alpha=False,
    alpha will be weighted spatially by the values of line integral convolution; otherwise a constant value of the given alpha is used.

    Arguments
    ---------
        U_grid: 'np.ndarray'
            Original data.
        V_grid: 'np.ndarray'
            Original data.
        method: 'float'
            sigma2 is defined as sum(sum((Y - V)**2)) / (N * D)
        cmap: 'float'
            Percentage of inliers in the samples. This is an inital value for EM iteration, and it is not important.
        normalize: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.
        density: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.
        lim: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.
        const_alpha: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.
        kernellen: 'float'
            Paramerter of the model of outliers. We assume the outliers obey uniform distribution, and the volume of outlier's variation space is a.

    Returns
    -------
    P: 'np.ndarray'
        Posterior probability, related to equation 27.
    E: `np.ndarray'
        Energy, related to equation 26.

    """

    if method == 'yt':
        velocity_x_ori, velocity_y_ori, velocity_z_ori = U_grid, V_grid, np.zeros(U_grid.shape)
        velocity_x = np.repeat(velocity_x_ori[:, :, np.newaxis], V_grid.shape[1], axis=2)
        velocity_y = np.repeat(velocity_y_ori[:, :, np.newaxis], V_grid.shape[1], axis=2)
        velocity_z = np.repeat(velocity_z_ori[np.newaxis, :, :], V_grid.shape[1], axis=0)

        data = {}

        data["velocity_x"] = (velocity_x, "km/s")
        data["velocity_y"] = (velocity_y, "km/s")
        data["velocity_z"] = (velocity_z, "km/s")
        data["velocity_sum"] = (np.sqrt(velocity_x**2 + velocity_y**2), "km/s")

        ds = yt.load_uniform_grid(data, data["velocity_x"][0].shape, length_unit=(1.0,"Mpc"))
        slc = yt.SlicePlot(ds, "z", ["velocity_sum"])
        slc.set_cmap("velocity_sum", cmap)
        slc.set_log("velocity_sum", False)

        slc.annotate_velocity(normalize = normalize)
        slc.annotate_streamlines('velocity_x', 'velocity_y', density=density)
        slc.annotate_line_integral_convolution('velocity_x', 'velocity_y', lim=lim, const_alpha=const_alpha, kernellen=kernellen)

        slc.set_xlabel(xlab)
        slc.set_ylabel(ylab)

        slc.show()

        if file is not None:
            # plt.rc('font', family='serif', serif='Times')
            # plt.rc('text', usetex=True)
            # plt.rc('xtick', labelsize=8)
            # plt.rc('ytick', labelsize=8)
            # plt.rc('axes', labelsize=8)
            slc.save(file, mpl_kwargs = {figsize: [2, 2]})
    elif method == 'lic':
        velocyto_tex = runlic(V_grid, V_grid, 100)
        plot_LIC_gray(velocyto_tex)

