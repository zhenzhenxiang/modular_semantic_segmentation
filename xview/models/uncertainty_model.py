import tensorflow as tf
import numpy as np
from sklearn.metrics import auc
from .base_model import BaseModel, transform_inputdata


class UncertaintyModel(BaseModel):

    @transform_inputdata()
    def misclassification_detection_score(self, data, uncertainty_attr,
                                          num_thresholds=100):
        with self.graph.as_default():
            uncertainty_attr = getattr(self, uncertainty_attr)

            uncertainty_for_correct_classes = []
            uncertainty_for_misclassification = []

            while True:
                try:
                    # get classification and uncertainty for given dataset
                    gt, prediction, uncertainty = self.sess.run(
                        [self.evaluation_labels, self.prediction, uncertainty_attr],
                        feed_dict={self.testing_handle: data})
                    uncertainty_for_correct_classes.append(uncertainty[gt == prediction])
                    uncertainty_for_misclassification.append(
                        uncertainty[gt != prediction])
                    break
                except tf.errors.OutOfRangeError:
                    break
            # reshape uncertainties into 1 big vector
            uncertainty_for_misclassification = np.concatenate(
                uncertainty_for_misclassification).flatten()
            uncertainty_for_correct_classes = np.concatenate(
                uncertainty_for_correct_classes).flatten()

            # now calculate ROC
            min_uncertainty = np.min((uncertainty_for_misclassification.min(),
                                      uncertainty_for_correct_classes.min()))
            max_uncertainty = np.max((uncertainty_for_misclassification.max(),
                                      uncertainty_for_correct_classes.max()))
            thresholds = np.linspace(min_uncertainty, max_uncertainty,
                                     num=num_thresholds)
            tpr = np.zeros(num_thresholds)
            fpr = np.zeros(num_thresholds)
            n_misclassified = uncertainty_for_misclassification.shape[0]
            n_correctly_classified = uncertainty_for_correct_classes.shape[0]
            for i in range(num_thresholds):
                tp = np.sum(uncertainty_for_misclassification > thresholds[i])
                fp = np.sum(uncertainty_for_correct_classes > thresholds[i])
                tpr[i] = tp / n_misclassified
                fpr[i] = fp / n_correctly_classified

            # area under curve
            auroc = auc(fpr, tpr, reorder=True)

            return fpr, tpr, auroc, thresholds
