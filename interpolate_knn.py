import os
import numpy as np
import open3d
import time
import multiprocessing

from util.metric import ConfusionMatrix
from util.point_cloud_util import load_labels
from dataset.semantic_dataset import validation_file_prefixes


if __name__ == "__main__":
    # TODO: handle test set
    sparse_dir = "result/sparse"
    dense_dir = "result/dense"
    gt_dir = "dataset/semantic_raw"

    # Parameters
    radius = 0.2
    k = 20

    # Global statistics
    cm_global = ConfusionMatrix(9)

    for file_prefix in validation_file_prefixes:
        print("Interpolating:", file_prefix)

        # Paths
        sparse_points_path = os.path.join(sparse_dir, file_prefix + ".pcd")
        sparse_labels_path = os.path.join(sparse_dir, file_prefix + ".labels")
        dense_points_path = os.path.join(gt_dir, file_prefix + ".pcd")
        dense_gt_labels_path = os.path.join(gt_dir, file_prefix + ".labels")

        # Sparse points
        sparse_pcd = open3d.read_point_cloud(sparse_points_path)
        print("sparse_pcd loaded")

        # Sparse labels
        sparse_labels = load_labels(sparse_labels_path)
        print("sparse_labels loaded")

        # Dense points
        dense_pcd = open3d.read_point_cloud(dense_points_path)
        dense_points = np.asarray(dense_pcd.points)
        print("dense_pcd loaded")

        # Dense Ground-truth labels
        dense_gt_labels = load_labels(os.path.join(gt_dir, file_prefix + ".labels"))
        print("dense_gt_labels loaded")

        # Build KNN tree
        sparse_pcd_tree = open3d.KDTreeFlann(sparse_pcd)
        print("sparse_pcd_tree ready")

        def match_knn_label(dense_index):
            global dense_points
            global sparse_labels
            global sparse_pcd_tree
            global radius
            global k

            dense_point = dense_points[dense_index]
            result_k, sparse_indexes, _ = sparse_pcd_tree.search_hybrid_vector_3d(
                dense_point, radius, k
            )
            if result_k == 0:
                result_k, sparse_indexes, _ = sparse_pcd_tree.search_knn_vector_3d(
                    dense_point, k
                )
            knn_sparse_labels = sparse_labels[sparse_indexes]
            dense_label = np.bincount(knn_sparse_labels).argmax()

            return dense_label

        # Assign labels
        start = time.time()
        dense_indexes = list(range(len(dense_points)))
        with multiprocessing.Pool() as pool:
            dense_labels = pool.map(match_knn_label, dense_indexes)
        print("knn match time: ", time.time() - start)

        # Eval
        cm = ConfusionMatrix(9)
        cm.increment_from_list(dense_gt_labels, dense_labels)
        cm.print_metrics()
        cm_global.increment_from_list(dense_gt_labels, dense_labels)

    print("Global results")
    cm_global.print_metrics()
