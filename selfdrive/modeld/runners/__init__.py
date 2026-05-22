import os
from openpilot.selfdrive.modeld.runners.runmodel_pyx import RunModel, Runtime
assert Runtime

class ModelRunner(RunModel):
  ONNX = 'ONNX'
  RKNN = 'RKNN'

  def __new__(cls, paths, *args, **kwargs):
    if ModelRunner.RKNN in paths:
      from openpilot.selfdrive.modeld.runners.rknnmodel_pyx import RKNNModel as Runner
      runner_type = ModelRunner.RKNN
    elif ModelRunner.ONNX in paths:
      from openpilot.selfdrive.modeld.runners.onnxmodel import ONNXModel as Runner
      runner_type = ModelRunner.ONNX
    else:
      raise Exception("Couldn't select a model runner, make sure to pass at least one valid model path")

    return Runner(str(paths[runner_type]), *args, **kwargs), runner_type
