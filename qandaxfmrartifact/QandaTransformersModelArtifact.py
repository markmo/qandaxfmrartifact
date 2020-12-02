import os
from importlib import import_module

import tensorflow as tf
import tensorflow_hub as hub
from bentoml.exceptions import (
    InvalidArgument,
    MissingDependencyException,
    NotFound,
)
from bentoml.service import BentoServiceArtifact

try:
    import transformers
except ImportError:
    transformers = None


class QandaTransformersModelArtifact(BentoServiceArtifact):
    """Abstraction for saving/loading Transformers models

    Args:
        name (string): name of the artifact

    Raises:
        MissingDependencyException: transformers package
            is required for TransformersModelArtifact

        InvalidArgument: invalid argument type, model being packed must be 
            a dictionary of format
            {
                'model': <transformers model object>,
                'tokenizer': <transformers tokenizer object>
            }
            or a directory path where the model is saved
            or a pre-trained model provided by transformers, which can be 
            loaded using transformers.AutoModelWithLMHead.

        NotFound: if the provided model name or model path is not found

    Example usage:
    >>> import bentoml
    >>> from transformers import AutoModelWithLMHead, AutoTokenizer
    >>> from bentoml.adapters import JsonInput
    >>>
    >>> @bentoml.env(pip_packages=["transformers==3.1.0", "torch==1.6.0"])
    >>> @bentoml.artifacts([TransformersModelArtifact("gptModel")])
    >>> class TransformerService(bentoml.BentoService):
    >>>     @bentoml.api(input=JsonInput(), batch=False)
    >>>     def predict(self, parsed_json):
    >>>         src_text = parsed_json.get("text")
    >>>         model = self.artifacts.gptModel.get("model")
    >>>         tokenizer = self.artifacts.gptModel.get("tokenizer")
    >>>         input_ids = tokenizer.encode(src_text, return_tensors="pt")
    >>>         output = model.generate(input_ids, max_length=50)
    >>>         output = tokenizer.decode(output[0], skip_special_tokens=True)
    >>>         return output
    >>>
    >>> ts = TransformerService()
    >>>
    >>> model_name = "gpt2"
    >>> model = AutoModelWithLMHead.from_pretrained("gpt2")
    >>> tokenizer = AutoTokenizer.from_pretrained("gpt2")
    >>>
    >>> # Option 1: Pack using dictionary (recommended)
    >>> artifact = {"model": model, "tokenizer": tokenizer}
    >>> ts.pack("gptModel", artifact)
    >>>
    >>> # Option 2: pack using the name of the model
    >>> # ts.pack("gptModel", "gpt2")
    >>>
    >>> # Note that while packing using the name of the model ensure that 
    >>> # the model can be loaded using transformers.AutoModelWithLMHead 
    >>> # (e.g. GPT, Bert, Roberta, etc.)
    >>>
    >>> # If this is not the case (e.g. AutoModelForQuestionAnswering, 
    >>> # BartModel, etc.) then pack the model by passing a dictionary
    >>> # with the model and the tokenizer declared explicitly.
    >>> saved_path = ts.save()
    """
    def __init__(self, name):
        super(QandaTransformersModelArtifact, self).__init__(name)
        self._model = None
        self._tokenizer_type = None
        self._model_type = 'AutoModelForQuestionAnswering'

        if transformers is None:
            raise MissingDependencyException(
                "the transformers package is required to use QandaTransformersModelArtifact"
            )

    def _file_path(self, base_path):
        return os.path.join(base_path, self.name)

    def _load_from_directory(self, path, opts):
        if self._model_type is None:
            raise NotFound(
                "Type of transformers model not found. "
                "This should be present in a file called "
                "'_model_type.txt' in the artifacts of the bundle."
            )

        if self._tokenizer_type is None:
            raise NotFound(
                "Type of transformers tokenizer not found. "
                "This should be present in a file called 'tokenizer_type.txt' "
                "in the artifacts of the bundle."
            )

        if 'embedder_model_path' not in opts:
            raise NotFound(
                "Path to embedder model should be in opts. "
            )

        transformers_model = \
            getattr(import_module('transformers'), self._model_type) \
            .from_pretrained(path)

        tokenizer = \
            getattr(import_module('transformers'), self._tokenizer_type) \
            .from_pretrained(path)
        
        embedder = hub.load(opts['embedder_model_path'])

        self._model = {'model': transformers_model, 'tokenizer': tokenizer, 'embedder': embedder}

    def _load_from_dict(self, model):
        if not model.get('model'):
            raise InvalidArgument(
                "'model' key is not found in the dictionary. "
                "Expecting a dictionary with keys 'model', 'tokenizer' and 'embedder'"
            )

        if not model.get('tokenizer'):
            raise InvalidArgument(
                "'tokenizer' key is not found in the dictionary. "
                "Expecting a dictionary with keys 'model', 'tokenizer' and 'embedder'"
            )

        if not model.get('embedder'):
            raise InvalidArgument(
                "'embedder' key is not found in the dictionary. "
                "Expecting a dictionary with keys 'model', 'tokenizer' and 'embedder'"
            )

        model_class = str(type(model.get('model')).__module__)
        tokenizer_class = str(type(model.get('tokenizer')).__module__)

        # if either model or tokenizer is not a property of the transformers package
        if not model_class.startswith('transformers'):
            raise InvalidArgument(
                'Expecting a transformers model object '
                'but got {}'.format(type(model.get('model')))
            )
        if not tokenizer_class.startswith('transformers'):
            raise InvalidArgument(
                'Expecting a transformers tokenizer object '
                'but got {}'.format(type(model.get('tokenizer')))
            )

        self._model = model

    def _load_from_string(self, model_name, opts):
        if 'embedder_model_path' not in opts:
            raise NotFound(
                "Path to embedder model should be in opts. "
            )

        try:
            transformers_model = \
                getattr(import_module('transformers'), self._model_type) \
                .from_pretrained(model_name)

            tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)

            embedder = hub.load(opts['embedder_model_path'])

            self._model = {'model': transformers_model, 'tokenizer': tokenizer, 'embedder': embedder}

        except EnvironmentError:
            raise NotFound(
                "model with name {} not present in "
                "the transformers library".format(model_name)
            )
        except AttributeError:
            raise NotFound(
                "transformers has no model type "
                "called {}".format(self._model_type)
            )

    def _save_package_opts(self, path, opts):
        with open(os.path.join(path, 'package_opts.json'), 'w') as f:
            json.dump(opts, f)

    def pack(self, model, opts=None):
        if opts is None:
            opts = {}

        if isinstance(model, str):
            if os.path.isdir(model):
                self._load_from_directory(model, opts)
            else:
                self._load_from_string(model, opts)
        elif isinstance(model, dict):
            self._load_from_dict(model)
        else:
            raise InvalidArgument(
                "Expecting a Dictionary of format "
                "{'model': <transformers model object>, 'tokenizer': <tokenizer object>}"
            )

        self._save_package_opts(model, opts)
        return self

    def load(self, path):
        path = self._file_path(path)

        with open(os.path.join(path, 'package_opts.json'), 'r') as f:
            opts = json.load(f)

        with open(os.path.join(path, '_model_type.txt'), 'r') as f:
            self._model_type = f.read().strip()

        with open(os.path.join(path, 'tokenizer_type.txt'), 'r') as f:
            self._tokenizer_type = f.read().strip()

        return self.pack(path, opts)

    def _save_model_type(self, path):
        with open(os.path.join(path, '_model_type.txt'), 'w') as f:
            f.write(self._model_type)

        with open(os.path.join(path, 'tokenizer_type.txt'), 'w') as f:
            f.write(self._tokenizer_type)

    def save(self, dst):
        path = self._file_path(dst)
        os.makedirs(path, exist_ok=True)
        self._model_type = self._model.get('model').__class__.__name__
        self._tokenizer_type = self._model.get('tokenizer').__class__.__name__
        self._model.get('model').save_pretrained(path)
        self._model.get('tokenizer').save_pretrained(path)
        tf.saved_model.save(self._model.get('embedder'), path)
        self._save_model_type(path)
        return path

    def get(self):
        return self._model