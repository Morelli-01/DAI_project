import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from sklearn.datasets import make_moons
import time, random
from numpy.random import randint, uniform


def two_moon_dataset(n_samples=100, shuffle=True, noise=None, random_state=None):
    """
    Make two interleaving half circles

    A simple toy dataset to visualize clustering and classification
    algorithms.

    Parameters
    ----------
    n_samples : int, optional (default=100)
        The total number of points generated.

    shuffle : bool, optional (default=True)
        Whether to shuffle the samples.

    noise : double or None (default=None)
        Standard deviation of Gaussian noise added to the data.

    Read more in the :ref:`User Guide <sample_generators>`.

    Returns
    -------
    X : array of shape [n_samples, 2]
        The generated samples.

    y : array of shape [n_samples]
        The integer labels (0 or 1) for class membership of each sample.
    """
    return make_moons(
        n_samples=n_samples, shuffle=shuffle, noise=noise, random_state=random_state
    )


def k_means(points: np.ndarray, n_cluster: int, debug=False, max_iter=10):
    start = time.time()

    n_points, dim = points.shape
    min_vector = np.array((np.min(points[:, 0]), np.min(points[:, 1])))
    max_vector = np.array((np.max(points[:, 0]), np.max(points[:, 1])))
    cluster_centers = (max_vector - min_vector) * np.random.random_sample(
        (n_cluster, dim)
    ) + min_vector
    tableau_colors = list(mcolors.TABLEAU_COLORS.values())
    if debug:
        plt.scatter(points[:, 0], points[:, 1], c="black")
        plt.scatter(cluster_centers[:, 0], cluster_centers[:, 1],
                    c=[tableau_colors.pop() for i in range(n_cluster)])
        plt.show()
        plt.close()
    labels = np.zeros(n_points)

    for k in range(max_iter):
        for i, point in enumerate(points):
            distances_ = np.zeros(n_cluster)
            for cluster in range(n_cluster):
                distances_[cluster] = (np.linalg.norm(cluster_centers[cluster] - point))
            # d1 = np.linalg.norm(cluster_centers[0] - point)
            # d2 = np.linalg.norm(cluster_centers[1] - point)
            labels[i] = np.argmin(distances_)
        if debug:
            tableau_colors = list(mcolors.TABLEAU_COLORS.values())

            plt.scatter(points[:, 0], points[:, 1], c=labels)
            plt.scatter(cluster_centers[:, 0], cluster_centers[:, 1],
                        c='red')
            plt.show()
            plt.close()

        clusters = []
        for cluster_label in range(n_cluster):
            clusters.append(points[labels == cluster_label])

        cluster_means = []
        for cluster_index in range(n_cluster):
            cluster = clusters[cluster_index]
            cluster_means.append(cluster.sum(axis=0) / cluster.shape[0])

        new_centers = np.array(cluster_means)
        if np.isclose(cluster_centers, new_centers).all():
            print("Done! Centers didnt move from previous iteration")
            end = time.time()
            length = end - start
            print("Kmeans with", points.shape[0], "points convergence took", length, "seconds!")
            return labels
        else:
            cluster_centers = new_centers

    end = time.time()
    length = end - start
    print("Kmeans with", points.shape[0], "points took", length, "seconds and didnt converge!")
    return labels


if __name__ == "__main__":
    # X, y = two_moon_dataset(n_samples=500, noise=0.1)
    #
    # plt.scatter(X[:,0], X[:,1], c=y)
    # plt.show()
    # plt.waitforbuttonpress()
    # plt.close()
    n_cluster = 2
    n_covariances = 10

    cov_2 = np.diag([0, 1])
    covariances = [np.diag([uniform(0.5, 5.0), uniform(0.5, 5.0)]) for i in range(n_covariances)]

    gaussians = [np.random.multivariate_normal([randint(0, 20), randint(0, 20)], random.choice(covariances),
                                               size=randint(2000, 20000))
                 for i in range(n_cluster)]

    tableau_colors = list(mcolors.TABLEAU_COLORS.values())
    [plt.scatter(gauss[:, 0], gauss[:, 1], c=tableau_colors.pop()) for gauss in gaussians]
    plt.show()
    plt.close()

    points = np.vstack((gaussians))
    np.random.shuffle(points)

    labels = k_means(points, n_cluster, debug=True, max_iter=1000)

    fig = plt.figure(layout="constrained")
    ax_array = fig.subplots(1, 2, squeeze=False)

    tableau_colors = list(mcolors.TABLEAU_COLORS.values())
    [ax_array[0, 0].scatter(gauss[:, 0], gauss[:, 1], c=tableau_colors.pop()) for gauss in gaussians]

    ax_array[0, 1].scatter(points[:, 0], points[:, 1], c=labels)
    fig.show()
