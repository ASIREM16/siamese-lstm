from keras.layers.merge import Add
import keras.backend as K


def energy_loss(y_true, y_pred):
    return K.exp(-K.abs(y_true - y_pred))


def mean_rectified_infinity_loss(y_true, y_pred):
    k = 5.0

    cond = K.equal(y_true, K.zeros_like(y_true))
    if K.backend() == 'tensorflow':
        import tensorflow as tf
        # err = tf.where(cond, K.square(y_pred - y_true), K.exp(-y_pred / k))
        err = tf.where(cond, K.square(y_pred),
                       k/K.square(K.clip(y_pred, min_value=K.epsilon(), max_value=float('inf'))))
    else:
        from theano.ifelse import ifelse
        # err = ifelse(cond, K.square(y_pred - y_true), K.exp(-y_pred / k))
        err = ifelse(cond, K.square(y_pred),
                     k/K.square(K.clip(y_pred, min_value=K.epsilon(), max_value=float('inf'))))

    return K.mean(err, axis=-1)


class Diff(Add):
    def _merge_function(self, inputs):
        return K.sum(K.abs(inputs[1] - inputs[0]), axis=-1, keepdims=True)

    # def _compute_elemwise_op_output_shape(self, shape1, shape2):
    #     return None, None, 1

    def compute_output_shape(self, input_shape):
        output_shape = (1,)

        batch_sizes = [s[0] for s in input_shape if s is not None]
        batch_sizes = set(batch_sizes)
        batch_sizes -= {None}
        if len(batch_sizes) == 1:
            output_shape = (list(batch_sizes)[0],) + output_shape
        else:
            output_shape = (None,) + output_shape
        return output_shape


class ExpDiff(Diff):
    def _merge_function(self, inputs):
        diff = K.abs(inputs[1] - inputs[0])
        sdiff = K.sqrt(K.sum(K.square(diff), axis=-1, keepdims=True))
        score = K.exp(-sdiff)
        neg_score = 1 - score
        return K.concatenate([score, neg_score])
        # return K.exp(-diff)

    def compute_output_shape(self, input_shape):
        output_shape = (2,)

        batch_sizes = [s[0] for s in input_shape if s is not None]
        batch_sizes = set(batch_sizes)
        batch_sizes -= {None}
        if len(batch_sizes) == 1:
            output_shape = (list(batch_sizes)[0],) + output_shape
        else:
            output_shape = (None,) + output_shape
        return output_shape

class CosineDist(Diff):
    def _merge_function(self, inputs):
        l, r = inputs[0], inputs[1]
        num = K.sum((l * r), keepdims=True, axis=-1)
        den = K.sqrt(K.sum(K.square(l), keepdims=True, axis=-1)) * K.sqrt(K.sum(K.square(r), keepdims=True, axis=-1))
        den = K.clip(den, min_value=1e-4, max_value=float('inf'))
        sim = num / den
        return K.ones_like(sim) - sim

    def _compute_elemwise_op_output_shape(self, shape1, shape2):
        return None, 1

    def compute_output_shape(self, input_shape):
        return None, 1
