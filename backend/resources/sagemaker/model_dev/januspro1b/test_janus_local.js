import { AutoProcessor, MultiModalityCausalLM } from "@huggingface/transformers";
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function testJanusLocal() {
    try {
        console.log("Loading Janus-Pro-1B model from local files...");

        // Path to the ARTIFACTS_MINIMAL directory (relative to this script)
        const modelPath = join(__dirname, "ARTIFACTS_MINIMAL");

        console.log("Model path:", modelPath);

        // Load processor and model from local path
        const processor = await AutoProcessor.from_pretrained(modelPath, {
            local_files_only: true
        });

        const model = await MultiModalityCausalLM.from_pretrained(modelPath, {
            local_files_only: true,
            dtype: "bnb4" // Use bnb4 for smallest size
        });

        console.log("Model loaded successfully!");

        // Simple test with a placeholder image URL (you can replace with local image)
        const conversation = [
            {
                role: "<|User|>",
                content: "<image_placeholder>\nDescribe what you see in this image.",
                images: ["https://huggingface.co/datasets/Xenova/transformers.js-docs/resolve/main/cats.jpg"],
            },
        ];

        console.log("Processing inputs...");
        const inputs = await processor(conversation);

        console.log("Generating response...");
        const outputs = await model.generate({
            ...inputs,
            max_new_tokens: 50,
            do_sample: false,
        });

        // Decode output
        const new_tokens = outputs.slice(null, [inputs.input_ids.dims.at(-1), null]);
        const decoded = processor.batch_decode(new_tokens, { skip_special_tokens: true });

        console.log("Generated response:", decoded[0]);
        // Generated response: In this image, I see two cats lying on a pink couch. There are two remote controls placed on the couch as well.

    } catch (error) {
        console.error("Error testing Janus model:", error);
    }
}

// Run the test
testJanusLocal();