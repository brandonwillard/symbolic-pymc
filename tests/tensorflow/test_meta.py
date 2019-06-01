import pytest
import numpy as np

import tensorflow as tf

from tensorflow_probability import distributions as tfd

from symbolic_pymc.tensorflow.meta import (TFlowMetaTensor,
                                           TFlowMetaTensorShape,
                                           TFlowMetaConstant,
                                           TFlowMetaOpDef,
                                           mt)

from tests.utils import assert_ops_equal


@pytest.mark.usefixtures("run_with_tensorflow")
def test_meta_create():
    N = 100
    X = np.vstack([np.random.randn(N), np.ones(N)]).T
    X_tf = tf.convert_to_tensor(X)
    X_mt = mt(X)

    assert isinstance(X_mt, TFlowMetaTensor)
    assert X_mt.op.obj.name.startswith('Const')
    # Make sure `reify` returns the cached base object.
    assert X_mt.reify() is X_mt.obj
    assert isinstance(X_mt.reify(), tf.Tensor)

    assert X_mt == mt(X_tf)

    # from google.protobuf import json_format
    # [i for i in X_tf.op.inputs]
    # print(json_format.MessageToJson(X_tf.op.op_def))

    # Create a (constant) tensor meta object manually.
    X_raw_mt = TFlowMetaConstant(obj=X)

    assert X_raw_mt._data is X

    # These are *not* equivalent, since they're constants without matching
    # constant values (well, our manually-created meta constant has no constant
    # value).
    assert X_mt == X_raw_mt
    # TODO: Should this be true?
    # assert X_mt.name == X_raw_mt.name

    add_mt = mt.add(1, 2)

    assert isinstance(add_mt, TFlowMetaTensor)
    assert isinstance(add_mt.obj, tf.Tensor)
    assert isinstance(add_mt.op.obj, tf.Operation)
    assert add_mt.op.obj.type == 'Add'

    assert len(add_mt.op.inputs) == 2
    assert all(isinstance(i, TFlowMetaTensor)
               for i in add_mt.op.inputs)

    one_mt, two_mt = mt(1), mt(2)

    assert one_mt != two_mt

    add_mt_2 = mt.add(one_mt, two_mt)

    assert isinstance(add_mt_2, TFlowMetaTensor)
    assert isinstance(add_mt_2.obj, tf.Tensor)
    assert isinstance(add_mt_2.op.obj, tf.Operation)
    assert add_mt_2.op.obj.type == 'Add'

    # These aren't technically equal because of the TF auto-generated names,
    # but, since we're using special string wrappers for the names, it should
    # work.
    assert add_mt == add_mt_2

    assert add_mt.obj is not None
    add_mt.name = None
    assert add_mt.obj is None
    add_mt_2.name = None

    assert add_mt == add_mt_2

    a_mt = mt(tf.compat.v1.placeholder('float64', name='a', shape=[1, 2]))
    b_mt = mt(tf.compat.v1.placeholder('float64', name='b'))
    assert a_mt != b_mt

    assert a_mt.shape.ndims == 2
    assert a_mt.shape == TFlowMetaTensorShape([1, 2])

    # TODO: Create a placeholder using the string `Operator` name.
    z_mt = TFlowMetaTensor('float64', 'Placeholder', name='z__')

    assert z_mt.op.type == 'Placeholder'
    assert z_mt.name.startswith('z__')
    assert z_mt.obj.name.startswith('z__')

    with pytest.raises(TypeError):
        TFlowMetaTensor('float64', 'Add', name='q__')

    # TODO: Test multi-output results
    assert True


@pytest.mark.usefixtures("run_with_tensorflow")
def test_meta_reify():
    a_mt = mt(tf.compat.v1.placeholder('float64', name='a', shape=[1, 2]))
    b_mt = mt(tf.compat.v1.placeholder('float64', name='b', shape=[]))
    add_mt = mt.add(a_mt, b_mt)

    assert add_mt.shape.as_list() == [1, 2]

    add_tf = add_mt.reify()

    assert isinstance(add_tf, tf.Tensor)
    assert add_tf.op.type == 'Add'
    assert add_tf.shape.as_list() == [1, 2]

    # Remove cached base object and force manual reification.
    add_mt.obj = None
    add_tf = add_mt.reify()

    assert isinstance(add_tf, tf.Tensor)
    assert add_tf.op.type == 'Add'
    assert add_tf.shape.as_list() == [1, 2]


@pytest.mark.usefixtures("run_with_tensorflow")
def test_meta_distributions():
    N = 100
    sigma_tf = tfd.Gamma(np.asarray(1.), np.asarray(1.)).sample()
    epsilon_tf = tfd.Normal(np.zeros((N, 1)), sigma_tf).sample()
    beta_tf = tfd.Normal(np.zeros((2, 1)), 1).sample()
    X = np.vstack([np.random.randn(N), np.ones(N)]).T
    X_tf = tf.convert_to_tensor(X)

    Y_tf = tf.linalg.matmul(X_tf, beta_tf) + epsilon_tf

    Y_mt = mt(Y_tf)

    # Confirm that all `Operation`s are the same.
    assert_ops_equal(Y_mt, Y_tf)

    # Now, let's see if we can reconstruct it entirely from the
    # meta objects.
    def _remove_obj(meta_obj):
        if (hasattr(meta_obj, 'obj') and
                not isinstance(meta_obj, TFlowMetaOpDef)):
            meta_obj.obj = None

        if hasattr(meta_obj, 'ancestors'):
            for a in meta_obj.ancestors or []:
                _remove_obj(a)

    _remove_obj(Y_mt)

    Y_mt_tf = Y_mt.reify()

    assert_ops_equal(Y_mt, Y_mt_tf)