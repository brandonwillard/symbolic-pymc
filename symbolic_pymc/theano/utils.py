import theano.tensor as tt

from theano.gof import FunctionGraph as tt_FunctionGraph, Query
from theano.gof.graph import inputs as tt_inputs, clone_get_equiv, io_toposort, ancestors
from theano.compile import optdb
from theano.scan_module.scan_op import Scan

from .meta import mt
from .opt import FunctionGraph
from .ops import RandomVariable
from .random_variables import Observed

from unification.utils import transitive_get as walk


canonicalize_opt = optdb.query(Query(include=["canonicalize"]))


def replace_input_nodes(inputs, outputs, replacements=None, memo=None, clone_inputs=True):
    """Recreate a graph, replacing input variables according to a given map.

    This is helpful if you want to replace the variable dependencies of
    an existing variable according to a `clone_get_equiv` map and/or
    replacement variables that already exist within a `FunctionGraph`.

    The latter is especially annoying, because you can't simply make a
    `FunctionGraph` for the variable to be adjusted and then use that to
    perform the replacement; if the variables to be replaced are already in a
    `FunctionGraph` any such replacement will err-out saying "...these
    variables are already owned by another graph..."

    Parameters
    ----------
    inputs: list
        List of input nodes.
    outputs: list
        List of output nodes.  Everything between `inputs` and these `outputs`
        is the graph under consideration.
    replacements: dict (optional)
        A dictionary mapping existing nodes to their new ones.
        These values in this map will be used instead of newly generated
        clones.  This dict is not altered.
    memo: dict (optional)
        A dictionary to update with the initial `replacements` and maps from
        any old-to-new nodes arising from an actual replacement.
        It serves the same role as `replacements`, but it is updated
        as elements are cloned.
    clone_inputs: bool (optional)
        If enabled, clone all the input nodes that aren't mapped in
        `replacements`.  These cloned nodes are mapped in `memo`, as well.

    Results
    -------
    out: memo

    """
    if memo is None:
        memo = {}
    if replacements is not None:
        memo.update(replacements)
    for apply in io_toposort(inputs, outputs):

        walked_inputs = []
        for i in apply.inputs:
            if clone_inputs:
                # TODO: What if all the inputs are in the memo?
                walked_inputs.append(memo.setdefault(i, i.clone()))
            else:
                walked_inputs.append(walk(i, memo))

        if any(w != i for w, i in zip(apply.inputs, walked_inputs)):
            new_apply = apply.clone_with_new_inputs(walked_inputs)

            memo.setdefault(apply, new_apply)
            for output, new_output in zip(apply.outputs, new_apply.outputs):
                memo.setdefault(output, new_output)
    return memo


def graph_equal(x, y):
    """Compare elements in a Theano graph using their object properties and not just identity."""
    try:
        if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
            return len(x) == len(y) and all(mt(xx) == mt(yy) for xx, yy in zip(x, y))
        return mt(x) == mt(y)
    except ValueError:
        return False


def optimize_graph(x, optimization, return_graph=None, in_place=False):
    """Easily optimize Theano graphs.

    Apply an optimization to either the graph formed by a Theano variable or an
    existing graph and return the resulting optimized graph.

    When given an existing `FunctionGraph`, the optimization is
    performed without side-effects (i.e. won't change the given graph).

    """
    if not isinstance(x, tt_FunctionGraph):
        inputs = tt_inputs([x])
        outputs = [x]
        model_memo = clone_get_equiv(inputs, outputs, copy_orphans=False)
        cloned_inputs = [model_memo[i] for i in inputs if not isinstance(i, tt.Constant)]
        cloned_outputs = [model_memo[i] for i in outputs]

        x_graph = FunctionGraph(cloned_inputs, cloned_outputs, clone=False)
        x_graph.memo = model_memo

        if return_graph is None:
            return_graph = False
    else:
        x_graph = x

        if return_graph is None:
            return_graph = True

    x_graph_opt = x_graph if in_place else x_graph.clone()
    _ = optimization.optimize(x_graph_opt)

    if return_graph:
        res = x_graph_opt
    else:
        res = x_graph_opt.outputs
        if len(res) == 1:
            (res,) = res
    return res


def canonicalize(x, **kwargs):
    """Canonicalize a Theano variable and/or graph."""
    return optimize_graph(x, canonicalize_opt, **kwargs)


def get_rv_observation(node):
    """Return a `RandomVariable` node's corresponding `Observed` node, or `None`."""
    if not getattr(node, "fgraph", None):
        raise ValueError("Node does not belong to a `FunctionGraph`")

    if isinstance(node.op, RandomVariable):
        fgraph = node.fgraph
        for o, i in node.default_output().clients:
            if o == "output":
                o = fgraph.outputs[i].owner

            if isinstance(o.op, Observed):
                return o
    return None


def is_random_variable(var):
    """Check if a Theano `Apply` node is a random variable.

    Output
    ------
    Tuple[TensorVariable, TensorVariable]
    Returns a tuple with the `RandomVariable` or `Scan` `Op` containing a
    `RandomVariable` variable--along with the corresponding output variable
    that is a client of said `Op`; otherwise, `None`.

    """
    node = var.owner

    if not var.owner:
        return None

    # Consider `Subtensor` `Op`s that slice a `Scan`.  This is the type of
    # output sometimes returned by `theano.scan` when taps/lags are used.
    if isinstance(node.op, tt.Subtensor) and node.inputs[0].owner:
        var = node.inputs[0]
        node = var.owner

    if isinstance(node.op, RandomVariable):
        return (var, var)

    if isinstance(node.op, Scan):
        op = node.op
        inner_out_var_idx = op.var_mappings["outer_out_from_inner_out"][node.outputs.index(var)]
        inner_out_var = op.outputs[inner_out_var_idx]

        if isinstance(inner_out_var.owner.op, RandomVariable):
            return (var, inner_out_var)

    return None


def vars_to_rvs(var):
    """Compute paths from `TensorVariable`s to their underlying `RandomVariable` outputs."""
    return {
        a: v if v[0] is not a else (v[1])
        for a, v in [(a, is_random_variable(a)) for a in ancestors([var])]
        if v is not None
    }


def get_random_outer_outputs(scan_args):
    """Get the `RandomVariable` outputs of a `Scan` (well, it's `ScanArgs`)."""
    rv_vars = []
    for n, oo in enumerate(scan_args.outer_outputs):
        oo_info = scan_args.find_among_fields(oo)
        io_type = oo_info.name[(oo_info.name.index("_", 6) + 1) :]
        inner_out_type = "inner_out_{}".format(io_type)
        io_var = getattr(scan_args, inner_out_type)[oo_info.index]
        if io_var.owner and isinstance(io_var.owner.op, RandomVariable):
            rv_vars.append((n, oo, io_var))
    return rv_vars


def construct_scan(scan_args):
    scan_op = Scan(scan_args.inner_inputs, scan_args.inner_outputs, scan_args.info)
    scan_out = scan_op(*scan_args.outer_inputs)

    if not isinstance(scan_out, list):
        scan_out = [scan_out]

    return scan_out
