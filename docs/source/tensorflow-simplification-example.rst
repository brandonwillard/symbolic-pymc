======================
Simplification Example
======================

    :Author: Brandon T. Willard
    :Date: 2019-09-08



1 Introduction
--------------

In this example, we'll illustrate the effect of algebraic graph simplifications
using the log-likelihood of a hierarchical normal-normal model.

.. code-block:: python
    :name: simplification-python-setup

    import numpy as np
    import tensorflow as tf

    import tensorflow_probability as tfp

    from tensorflow.python.eager.context import graph_mode
    from tensorflow.python.framework.ops import disable_tensor_equality

    from symbolic_pymc.tensorflow.printing import tf_dprint
    from symbolic_pymc.tensorflow.graph import normalize_tf_graph


    disable_tensor_equality()

We start by performing the graph normalization/simplifications native to
TensorFlow via the \ ``grappler``\  module.
:ref:`hier-normal-graph` creates our model and normalizes it.

.. code-block:: python
    :name: hier-normal-graph

    def tfp_normal_log_prob(x, loc, scale):
        log_unnormalized = -0.5 * tf.math.squared_difference(
            x / scale, loc / scale)
        log_normalization = 0.5 * np.log(2. * np.pi)
        # log_normalization += tf.math.log(scale)
        return log_unnormalized - log_normalization


    with graph_mode(), tf.Graph().as_default() as demo_graph:

        x_tf = tf.compat.v1.placeholder(tf.float32, name='value_x',
                                        shape=tf.TensorShape([None]))
        tau_tf = tf.compat.v1.placeholder(tf.float32, name='tau',
                                          shape=tf.TensorShape([None]))
        y_tf = tf.compat.v1.placeholder(tf.float32, name='value_y',
                                        shape=tf.TensorShape([None]))

        X_tfp = tfp.distributions.normal.Normal(0.0, 1.0, name='X')

        z_tf = x_tf + tau_tf * y_tf

        hier_norm_lik = tf.math.log(z_tf)

        # Unscaled normal log-likelihood
        log_unnormalized = -0.5 * tf.math.squared_difference(
            z_tf / tau_tf, x_tf / tau_tf)
        log_normalization = 0.5 * np.log(2. * np.pi)
        hier_norm_lik += log_unnormalized - log_normalization

        hier_norm_lik += X_tfp.log_prob(x_tf)

        hier_norm_lik = normalize_tf_graph(hier_norm_lik)

In :ref:`hier-normal-graph` we used an unscaled version of the normal
log-likelihood.  This is because we're emulating the effect of applying a
substitution like :math:`Y \to x + \tau \epsilon \sim \operatorname{N}\left(x, \tau^2\right)`.
This has the same effect as subtracting a :math:`\log(\tau)` term; however, the
result will produce equivalent--but not equal--graphs when we compare with the
manually created fully transformed graph in :ref:`manually-simplified-graph`.

.. code-block:: python
    :name: hier-normal-graph-print

    tf_dprint(hier_norm_lik)

.. code-block:: text

    Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_2:0"
    |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"X_1/log_prob/sub:0"
    |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_1/log_prob/mul:0"
    |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"X_1/log_prob/SquaredDifference:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_1/log_prob/truediv:0"
    |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"ConstantFolding/X_1/log_prob/truediv_recip:0"
    |  |  |  |  |  |  1.
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"X_1/log_prob/truediv_1:0"
    |  |  |  |  |  0.
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"mul_1/x:0"
    |  |  |  |  -0.5
    |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"sub/y:0"
    |  |  |  0.9189385
    |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_1:0"
    |  |  Tensor(Log):0,	dtype=float32,	shape=[None],	"Log:0"
    |  |  |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"mul:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"tau:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_y:0"
    |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"sub:0"
    |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"mul_1:0"
    |  |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"SquaredDifference:0"
    |  |  |  |  |  Tensor(RealDiv):0,	dtype=float32,	shape=[None],	"truediv:0"
    |  |  |  |  |  |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add:0"
    |  |  |  |  |  |  |  ...
    |  |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"tau:0"
    |  |  |  |  |  Tensor(RealDiv):0,	dtype=float32,	shape=[None],	"truediv_1:0"
    |  |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"tau:0"
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"mul_1/x:0"
    |  |  |  |  |  -0.5
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"sub/y:0"
    |  |  |  |  0.9189385

From :ref:`hier-normal-graph-print` we can see
that \ ``grappler``\  is not applying enough algebraic
simplifications (e.g. it doesn't remove multiplications with :math:`1` or reduce the
:math:`\left(\mu + x - \mu \right)^2` term
in \ ``SquaredDifference``\ ).

****Does missing this simplification amount to anything practical?****

:ref:`manually-simplified-graph-eval` demonstrates the difference between our model
without the simplification and a manually constructed model with the simplification (i.e.
:ref:`manually-simplified-graph`).

.. code-block:: python
    :name: manually-simplified-graph

    with graph_mode(), demo_graph.as_default():

        Z_tfp = tfp.distributions.normal.Normal(0.0, 1.0, name='Y_trans')

        hn_manually_simplified_lik = tf.math.log(z_tf)
        hn_manually_simplified_lik += Z_tfp.log_prob(y_tf)
        hn_manually_simplified_lik += X_tfp.log_prob(x_tf)

        hn_manually_simplified_lik = normalize_tf_graph(hn_manually_simplified_lik)

.. code-block:: python
    :name: manually-simplified-graph-print

    tf_dprint(hn_manually_simplified_lik)

.. code-block:: text

    Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_4:0"
    |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"X_2/log_prob/sub:0"
    |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_2/log_prob/mul:0"
    |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"X_2/log_prob/SquaredDifference:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_2/log_prob/truediv:0"
    |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"ConstantFolding/Y_trans_1/log_prob/truediv_recip:0"
    |  |  |  |  |  |  1.
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/truediv_1:0"
    |  |  |  |  |  0.
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/mul/x:0"
    |  |  |  |  -0.5
    |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/add:0"
    |  |  |  0.9189385
    |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_3:0"
    |  |  Tensor(Log):0,	dtype=float32,	shape=[None],	"Log_1:0"
    |  |  |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"mul:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"tau:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_y:0"
    |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"Y_trans_1/log_prob/sub:0"
    |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"Y_trans_1/log_prob/mul:0"
    |  |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"Y_trans_1/log_prob/SquaredDifference:0"
    |  |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"Y_trans_1/log_prob/truediv:0"
    |  |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"ConstantFolding/Y_trans_1/log_prob/truediv_recip:0"
    |  |  |  |  |  |  |  1.
    |  |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_y:0"
    |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/truediv_1:0"
    |  |  |  |  |  |  0.
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/mul/x:0"
    |  |  |  |  |  -0.5
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"Y_trans_1/log_prob/add:0"
    |  |  |  |  0.9189385

.. code-block:: python
    :name: manually-simplified-graph-eval

    test_point = {x_tf.name: np.r_[1.0],
                  tau_tf.name: np.r_[1e-9],
                  y_tf.name: np.r_[1000.1]}

    with tf.compat.v1.Session(graph=hn_manually_simplified_lik.graph).as_default():
        hn_manually_simplified_val = hn_manually_simplified_lik.eval(test_point)

    with tf.compat.v1.Session(graph=hier_norm_lik.graph).as_default():
        hn_unsimplified_val = hier_norm_lik.eval(test_point)

    _ = np.subtract(hn_unsimplified_val, hn_manually_simplified_val)

.. code-block:: text

    [39299.97]

The output of :ref:`manually-simplified-graph-eval` shows exactly how large
the discrepancy can be for carefully chosen parameter values.  More
specifically, as \ ``tau_tf``\  gets smaller and the magnitude
of the difference \ ``x_tf - y_tf``\  gets larger, the
discrepancy can increase.  Since such parameter values are likely to be visited
during sampling, we should address this missing simplification.

In :ref:`further-simplify-test-graph` we create a goal that performs that
aforementioned simplification for \ ``SquaredDifference``\ .

.. code-block:: python
    :name: recenter-sqrdiffo

    from functools import partial
    from collections import Sequence

    from unification import var

    from kanren import run, eq, lall, conde
    from kanren.facts import fact
    from kanren.assoccomm import eq_comm, commutative
    from kanren.graph import walko

    from etuples import etuple, etuplize
    from etuples.core import ExpressionTuple

    from symbolic_pymc.meta import enable_lvar_defaults
    from symbolic_pymc.tensorflow.meta import mt, TFlowMetaOperator


    fact(commutative, TFlowMetaOperator(mt.SquaredDifference.op_def, var()))


    def recenter_sqrdiffo(in_g, out_g):
        """Create a goal that essentially reduces `(a / d - (a + d * c) / d)**2` to `d**2`"""
        a_sqd_lv, b_sqd_lv, d_sqd_lv = var(), var(), var()

        with enable_lvar_defaults('names'):
            # Pattern: (a / d - b / d)**2
            target_sqrdiff_lv = mt.SquaredDifference(
                mt.Realdiv(a_sqd_lv, d_sqd_lv),
                mt.Realdiv(b_sqd_lv, d_sqd_lv))

            # Pattern: d * c + a
            c_sqd_lv = var()
            b_part_lv = mt.AddV2(mt.Mul(d_sqd_lv, c_sqd_lv), a_sqd_lv)

        # Replacement: c**2
        simplified_sqrdiff_lv = mt.SquaredDifference(
            c_sqd_lv,
            0.0
        )

        reshape_lv = var()
        simplified_sqrdiff_reshaped_lv = mt.SquaredDifference(
            mt.reshape(c_sqd_lv, reshape_lv),
            0.0
        )

        with enable_lvar_defaults('names'):
            b_sqd_reshape_lv = mt.Reshape(b_part_lv, reshape_lv)

        res = lall(
            # input == (a / d - b / d)**2 must be "true"
            eq_comm(in_g, target_sqrdiff_lv),
            # "and"
            conde([
                # "if" b == d * c + a is "true"
                eq(b_sqd_lv, b_part_lv),
                # "then" output ==  (c - 0)**2 is also "true"
                eq(out_g, simplified_sqrdiff_lv)

                # "or"
            ], [
                # We have to use this to cover some variation also not
                # sufficiently/consistently "normalized" by `grappler`.

                # "if" b == reshape(d * c + a, ?) is "true"
                eq_comm(b_sqd_lv, b_sqd_reshape_lv),
                # "then" output == (reshape(c, ?) - 0)**2 is also "true"
                eq(out_g, simplified_sqrdiff_reshaped_lv)
            ]))
        return res

We apply the simplification in :ref:`further-simplify-test-graph` and print
the results in :ref:`further-simplify-test-graph-print`.

.. code-block:: python
    :name: further-simplify-test-graph

    from kanren.graph import reduceo


    with graph_mode(), hier_norm_lik.graph.as_default():
        q = var()
        res = run(1, q,
                  reduceo(lambda x, y: walko(recenter_sqrdiffo, x, y),
                          hier_norm_lik, q))

    with graph_mode(), tf.Graph().as_default() as result_graph:
        hn_simplified_tf = res[0].eval_obj.reify()
        hn_simplified_tf = normalize_tf_graph(hn_simplified_tf)

.. code-block:: python
    :name: further-simplify-test-graph-print

    # tf_dprint(hier_norm_lik.graph.get_tensor_by_name('SquaredDifference:0'))
    tf_dprint(hn_simplified_tf)

.. code-block:: text

    Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_2_1:0"
    |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"X_1/log_prob/sub:0"
    |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_1/log_prob/mul:0"
    |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"X_1/log_prob/SquaredDifference:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"X_1/log_prob/truediv:0"
    |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"ConstantFolding/X_1/log_prob/truediv_recip:0"
    |  |  |  |  |  |  1.
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"X_1/log_prob/truediv_1:0"
    |  |  |  |  |  0.
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"mul_1/x:0"
    |  |  |  |  -0.5
    |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"sub/y:0"
    |  |  |  0.9189385
    |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add_1_1:0"
    |  |  Tensor(Log):0,	dtype=float32,	shape=[None],	"Log:0"
    |  |  |  Tensor(AddV2):0,	dtype=float32,	shape=[None],	"add:0"
    |  |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"mul:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"tau:0"
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_y:0"
    |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_x:0"
    |  |  Tensor(Sub):0,	dtype=float32,	shape=[None],	"sub_1:0"
    |  |  |  Tensor(Mul):0,	dtype=float32,	shape=[None],	"mul_1_1:0"
    |  |  |  |  Tensor(SquaredDifference):0,	dtype=float32,	shape=[None],	"SquaredDifference_1:0"
    |  |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"X_1/log_prob/truediv_1:0"
    |  |  |  |  |  |  0.
    |  |  |  |  |  Tensor(Placeholder):0,	dtype=float32,	shape=[None],	"value_y:0"
    |  |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"mul_1/x:0"
    |  |  |  |  |  -0.5
    |  |  |  Tensor(Const):0,	dtype=float32,	shape=[],	"sub/y:0"
    |  |  |  |  0.9189385

After applying our simplification, :ref:`simplified-eval-print` numerically
demonstrates that the difference is gone and that our transform produces a graph
equivalent to the manually simplified graph in :ref:`manually-simplified-graph`.

.. code-block:: python
    :name: simplified-eval-print

    with tf.compat.v1.Session(graph=hn_simplified_tf.graph).as_default():
        hn_simplified_val = hn_simplified_tf.eval(test_point)

    _ = np.subtract(hn_manually_simplified_val, hn_simplified_val)

.. code-block:: text

    [0.]
