
import requests
import json
import numpy

from sklearn.tree._tree import Tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

def serialize_tree(tree):
    serialized_tree = tree.__getstate__()

    dtypes = serialized_tree['nodes'].dtype
    serialized_tree['nodes'] = serialized_tree['nodes'].tolist()
    serialized_tree['values'] = serialized_tree['values'].tolist()

    return serialized_tree, dtypes


def deserialize_tree(tree_dict, n_features, n_classes, n_outputs):
    tree_dict['nodes'] = [tuple(lst) for lst in tree_dict['nodes']]

    names = ['left_child', 'right_child', 'feature', 'threshold', 'impurity', 'n_node_samples', 'weighted_n_node_samples', 'missing_go_to_left']
    tree_dict['nodes'] = numpy.array(tree_dict['nodes'], dtype=numpy.dtype({'names': names, 'formats': tree_dict['nodes_dtype']}))
    tree_dict['values'] = numpy.array(tree_dict['values'])

    tree = Tree(n_features, numpy.array([n_classes], dtype=numpy.intp), n_outputs)
    tree.__setstate__(tree_dict)

    return tree

def serialize_decision_tree(model):
    tree, dtypes = serialize_tree(model.tree_)
    serialized_model = {
        'meta': 'decision-tree',
        'feature_importances_': model.feature_importances_.tolist(),
        'max_features_': model.max_features_,
        'n_classes_': int(model.n_classes_),
        'n_features_in_': model.n_features_in_,
        'n_outputs_': model.n_outputs_,
        'tree_': tree,
        'classes_': model.classes_.tolist(),
        'params': model.get_params()
    }


    tree_dtypes = []
    for i in range(0, len(dtypes)):
        tree_dtypes.append(dtypes[i].str)

    serialized_model['tree_']['nodes_dtype'] = tree_dtypes

    return serialized_model


def deserialize_decision_tree(model_dict):
    deserialized_model = DecisionTreeClassifier(**model_dict['params'])

    deserialized_model.classes_ = numpy.array(model_dict['classes_'])
    deserialized_model.max_features_ = model_dict['max_features_']
    deserialized_model.n_classes_ = model_dict['n_classes_']
    deserialized_model.n_features_in_ = model_dict['n_features_in_']
    deserialized_model.n_outputs_ = model_dict['n_outputs_']

    tree = deserialize_tree(model_dict['tree_'], model_dict['n_features_in_'], model_dict['n_classes_'], model_dict['n_outputs_'])
    deserialized_model.tree_ = tree

    return deserialized_model

def serialize_random_forest(model):
    serialized_model = {
        'meta': 'rf',
        'max_depth': model.max_depth,
        'min_samples_split': model.min_samples_split,
        'min_samples_leaf': model.min_samples_leaf,
        'min_weight_fraction_leaf': model.min_weight_fraction_leaf,
        'max_features': model.max_features,
        'max_leaf_nodes': model.max_leaf_nodes,
        'min_impurity_decrease': model.min_impurity_decrease,
        # 'min_impurity_split': model.min_impurity_split,
        'n_features_in_': model.n_features_in_,
        'n_outputs_': model.n_outputs_,
        'classes_': model.classes_.tolist(),
        'estimators_': [serialize_decision_tree(decision_tree) for decision_tree in model.estimators_],
        'params': model.get_params()
    }

    if 'oob_score_' in model.__dict__:
        serialized_model['oob_score_'] = model.oob_score_
    if 'oob_decision_function_' in model.__dict__:
        serialized_model['oob_decision_function_'] = model.oob_decision_function_.tolist()

    if isinstance(model.n_classes_, int):
        serialized_model['n_classes_'] = model.n_classes_
    else:
        serialized_model['n_classes_'] = model.n_classes_.tolist()

    return serialized_model

def deserialize_random_forest(model_dict):
    model = RandomForestClassifier(**model_dict['params'])
    estimators = [deserialize_decision_tree(decision_tree) for decision_tree in model_dict['estimators_']]
    model.estimators_ = numpy.array(estimators)

    model.classes_ = numpy.array(model_dict['classes_'])
    model.n_features_in_ = model_dict['n_features_in_']
    model.n_outputs_ = model_dict['n_outputs_']
    model.max_depth = model_dict['max_depth']
    model.min_samples_split = model_dict['min_samples_split']
    model.min_samples_leaf = model_dict['min_samples_leaf']
    model.min_weight_fraction_leaf = model_dict['min_weight_fraction_leaf']
    model.max_features = model_dict['max_features']
    model.max_leaf_nodes = model_dict['max_leaf_nodes']
    model.min_impurity_decrease = model_dict['min_impurity_decrease']
    # model.min_impurity_split = model_dict['min_impurity_split']

    if 'oob_score_' in model_dict:
        model.oob_score_ = model_dict['oob_score_']
    if 'oob_decision_function_' in model_dict:
        model.oob_decision_function_ = model_dict['oob_decision_function_']

    if isinstance(model_dict['n_classes_'], list):
        model.n_classes_ = numpy.array(model_dict['n_classes_'])
    else:
        model.n_classes_ = model_dict['n_classes_']

    return model

def format_data(data):
    for key, value in data.items():
        if isinstance(data[key], numpy.ndarray):
            data[key] = value.tolist()
        elif isinstance(value, RandomForestClassifier):
            data[key] = serialize_random_forest(value)
    return json.dumps(data)

def send_request(server, data):
    # Send the image to the server
    try:
        response = requests.post(f"{server}/process", data=format_data(data))
    except requests.exceptions.ConnectionError:
        return None
    # Get the result
    data = json.loads(response.text)
    return data

def process_request(data):
    for key, value in data.items():
        if key in ["prediction", "probability"]:
            data[key] = numpy.array(value)
        if key == "model":
            data[key] = deserialize_random_forest(value)
    return data