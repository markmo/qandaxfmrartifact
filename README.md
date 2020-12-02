# qandaxfmrartifact

BentoML artifact framework for Q&A Transformers.

Installation:

    pip install qandaxfmrartifact==0.0.1

Usage example (decorate service):

    from qandaxfmrartifact.QandaTransformersModelArtifact import QandaTransformersModelArtifact

    @artifacts([QandaTransformersModelArtifact('albert')])
    class MyBentoService(BentoService):


Usage example (package model):

    svc = MyBentoService()

    opts = {
        'embedder_model_path': my_embedder_model_path,
    }

    svc.pack('albert', my_transformer_model_path, opts)

Alternatively, during training:

    svc.pack('albert', {'model': my_trained_model, 'tokenizer': my_tokenizer, 'embedder': my_embedder})
