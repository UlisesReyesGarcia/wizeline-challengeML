import { fetchAuthSession } from "aws-amplify/auth";

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

async function getIdToken() {
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken?.toString();

  if (!idToken) {
    throw new Error("No active ID token found.");
  }

  return idToken;
}

export async function apiRequest(path, options = {}) {
  const idToken = await getIdToken();

  const response = await fetch(`${API_ENDPOINT}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const text = await response.text();

  let data = null;
  if (text) {
    data = JSON.parse(text);
  }

  if (!response.ok) {
    throw new Error(data?.message || `Request failed with status ${response.status}`);
  }

  return data;
}

export async function getChampionModel() {
  return apiRequest("/model-registry/champion", {
    method: "GET",
  });
}

export async function createUploadUrl({ uploadType, fileName }) {
  return apiRequest("/upload-url", {
    method: "POST",
    body: JSON.stringify({
      upload_type: uploadType,
      file_name: fileName,
    }),
  });
}

export async function uploadCsvToPresignedUrl({ uploadUrl, file }) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": "text/csv",
    },
    body: file,
  });

  if (!response.ok) {
    throw new Error(`S3 upload failed with status ${response.status}`);
  }

  return true;
}

export async function runBatchPrediction({ inputS3Uri }) {
  return apiRequest("/predictions", {
    method: "POST",
    body: JSON.stringify({
      action: "predict",
      input_s3_uri: inputS3Uri,
    }),
  });
}

export async function getPredictionResult({ outputS3Uri }) {
  return apiRequest("/predictions", {
    method: "POST",
    body: JSON.stringify({
      action: "get_result",
      output_s3_uri: outputS3Uri,
    }),
  });
}

export async function startRetraining({ trainingDataUri }) {
  return apiRequest("/retrain", {
    method: "POST",
    body: JSON.stringify({
      training_data_uri: trainingDataUri,
    }),
  });
}
