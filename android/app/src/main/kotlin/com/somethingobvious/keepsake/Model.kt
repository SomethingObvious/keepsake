package com.somethingobvious.keepsake

import ai.onnxruntime.OnnxJavaType
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * One of Remove Text's two models, in ONNX Runtime for Android. The desktop's Python calls run() as it
 * would call onnxruntime's InferenceSession on Windows, through android_shell.py, which turns its numpy
 * arrays into Tensors and back.
 */
class Model(path: String) {
    private val session = env.createSession(path, OrtSession.SessionOptions())

    /** A tensor as it crosses from Python: its shape, its bytes in the phone's own order, and uint8 or float32. */
    class Tensor(@JvmField val shape: LongArray, @JvmField val data: ByteArray, @JvmField val uint8: Boolean)

    /** Runs the model on its named inputs, and returns every output in the model's order. */
    fun run(names: Array<String>, inputs: Array<Tensor>): Array<Tensor> {
        val feed = names.zip(inputs).associate { (name, input) ->
            val buffer = ByteBuffer.allocateDirect(input.data.size).order(ByteOrder.nativeOrder())
            buffer.put(input.data).rewind()
            name to OnnxTensor.createTensor(env, buffer, input.shape, if (input.uint8) OnnxJavaType.UINT8 else OnnxJavaType.FLOAT)
        }
        return try {
            session.run(feed).use { results ->
                results.map { (_, value) ->
                    val tensor = value as OnnxTensor
                    Tensor(tensor.info.shape, tensor.byteBuffer.array(), tensor.info.type == OnnxJavaType.UINT8)
                }.toTypedArray()
            }
        } finally {
            feed.values.forEach { it.close() }
        }
    }

    private companion object {
        val env: OrtEnvironment = OrtEnvironment.getEnvironment().apply { setTelemetry(false) }
    }
}
