import { DynamoDBClient, QueryCommand } from "@aws-sdk/client-dynamodb";
import {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand,
} from "@aws-sdk/client-bedrock-agentcore";
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";
import { createAwsClient } from "./AwsAuth";
import {
  extractBetweenTags,
  removeCharFromStartAndEnd,
  handleFormatter,
} from "./Utils.js";
import {
  QUESTION_ANSWERS_TABLE_NAME,
  MODEL_ID_FOR_CHART,
  CHART_PROMPT,
  AGENT_RUNTIME_ARN,
  AGENT_ENDPOINT_NAME,
} from "../env.js";

/**
 * Query data from DynamoDB
 *
 * @param {string} id - The ID to query
 * @returns {Promise<Object>} - The query response
 */
export const getQueryResults = async (queryUuid = "") => {
  let queryResults = [];
  try {
    const dynamodb = await createAwsClient(DynamoDBClient);
    const input = {
      TableName: QUESTION_ANSWERS_TABLE_NAME,
      KeyConditionExpression: "id = :queryUuid",
      ExpressionAttributeValues: {
        ":queryUuid": {
          S: queryUuid,
        },
      },
      ConsistentRead: true,
    };
    console.log("------- Get Query Results -------");
    console.log(input);
    const command = new QueryCommand(input);
    const response = await dynamodb.send(command);
    if (response.hasOwnProperty("Items")) {
      for (let i = 0; i < response.Items.length; i++) {
        queryResults.push({
          query: response.Items[i].sql_query.S,
          query_results: JSON.parse(response.Items[i].data.S).result,
          query_description: response.Items[i].sql_query_description.S,
        });
      }
    }
    return queryResults;
  } catch (error) {
    console.error("Error querying DynamoDB:", error);
    throw error;
  }
};

/**
 * Generates a chart based on answer and data
 * @param {Object} answer - Answer object containing text
 * @returns {Object} Chart configuration or rationale for no chart
 */
export const generateChart = async (answer) => {
  const bedrock = await createAwsClient(BedrockRuntimeClient);
  let query_results = "";
  for (let i = 0; i < answer.queryResults.length; i++) {
    query_results +=
      JSON.stringify(answer.queryResults[i].query_results) + "\n";
  }

  // Prepare the prompt
  let new_chart_prompt = CHART_PROMPT.replace(
    /<<answer>>/i,
    answer.text
  ).replace(/<<data_sources>>/i, query_results);

  const payload = {
    anthropic_version: "bedrock-2023-05-31",
    max_tokens: 2000,
    temperature: 1,
    messages: [
      {
        role: "user",
        content: [{ type: "text", text: new_chart_prompt }],
      },
    ],
  };

  try {
    // Send the request to Bedrock
    console.log("------- Request chart -------");
    console.log(payload);

    const command = new InvokeModelCommand({
      contentType: "application/json",
      body: JSON.stringify(payload),
      modelId: MODEL_ID_FOR_CHART,
    });

    const apiResponse = await bedrock.send(command);
    const decodedResponseBody = new TextDecoder().decode(apiResponse.body);
    const responseBody = JSON.parse(decodedResponseBody).content[0].text;
    console.log("------- Response chart generation -------");
    console.log(responseBody);

    // Process the response
    const has_chart = parseInt(extractBetweenTags(responseBody, "has_chart"));

    if (has_chart) {
      const chartConfig = JSON.parse(
        extractBetweenTags(responseBody, "chart_configuration")
      );
      const chart = {
        chart_type: removeCharFromStartAndEnd(
          extractBetweenTags(responseBody, "chart_type"),
          "\n"
        ),
        chart_configuration: handleFormatter(chartConfig),
        caption: removeCharFromStartAndEnd(
          extractBetweenTags(responseBody, "caption"),
          "\n"
        ),
      };

      console.log("------- Final chart generation -------");
      console.log(chart);

      return chart;
    } else {
      return {
        rationale: removeCharFromStartAndEnd(
          extractBetweenTags(responseBody, "rationale"),
          "\n"
        ),
      };
    }
  } catch (error) {
    console.error("Chart generation failed:", error);
    return {
      rationale: "Error generating or parsing chart data.",
    };
  }
};

/**
 * Invokes the agent core functionality with streaming support
 * @param {string} query - The user query to send to the agent
 * @param {string} sessionId - The session ID for the conversation
 * @param {string} queryUuid - The unique UUID for this query
 * @param {string} timezone - The user's timezone
 * @param {Function} setAnswers - State setter for answers (for streaming)
 * @param {Function} setControlAnswers - State setter for control answers (for streaming)
 * @param {number} lastKTurns - Number of previous conversation turns to maintain (default: 10)
 * @returns {Promise<Object>} - The agent's response with comprehensive data
 */
export const invokeAgentCore = async (
  query,
  sessionId = null,
  queryUuid = null,
  timezone = null,
  setAnswers,
  setControlAnswers,
  lastKTurns = 10
) => {
  try {
    const agentCore = await createAwsClient(BedrockAgentCoreClient);
    console.log("Invoking agent core with query:", query);

    // Create the payload with the actual parameters including conversation history
    const payload = JSON.stringify({
      prompt: query,
      session_id: sessionId || "default-session",
      prompt_uuid: queryUuid || "default-uuid",
      user_timezone: timezone || "UTC",
      last_k_turns: lastKTurns,
    });

    const input = {
      agentRuntimeArn: AGENT_RUNTIME_ARN,
      qualifier: AGENT_ENDPOINT_NAME,
      payload,
    };

    console.log("Agent Core Input:", input);

    const command = new InvokeAgentRuntimeCommand(input);
    const response = await agentCore.send(command);

    let completion = "";
    let hasReceivedFirstChunk = false;

    // Initialize streaming output
    console.log("------- Agent Response (Streaming) -------");

    try {
      // Check if response has streaming capability
      if (response.response) {
        // Handle streaming response
        const stream = response.response.transformToWebStream();
        const reader = stream.getReader();
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            console.log("---------->");
            console.log("Chunk received:", chunk);
            const lines = [];
            chunk.split("\n").forEach((line) => {
              if (line.trim() && line.startsWith("data: ")) {
                if (line.trim() && line.startsWith("data: ")) {
                  const jsonString = line.replace(/^data: /, '{"data": ') + "}";

                  try {
                    const obj = JSON.parse(jsonString);
                    lines.push(obj.data);
                  } catch (error) {
                    console.error("Error parsing JSON:", error);
                  }
                }
              }
            });
            lines.forEach((line) => {
              completion += line;
            });

            // Add initial answer object only after receiving the first chunk
            if (!hasReceivedFirstChunk) {
              hasReceivedFirstChunk = true;
              setAnswers((prevState) => [
                ...prevState,
                { text: completion, isStreaming: true },
              ]);
              setControlAnswers((prevState) => [
                ...prevState,
                { current_tab_view: "answer" },
              ]);
            } else {
              // Update the existing streaming answer with new text
              setAnswers((prevState) => {
                const newState = [...prevState];
                // Find the last answer that is streaming and update it
                for (let i = newState.length - 1; i >= 0; i--) {
                  if (newState[i].isStreaming) {
                    newState[i] = {
                      ...newState[i],
                      text: completion,
                    };
                    break;
                  }
                }
                return newState;
              });
            }
          }
        } finally {
          reader.releaseLock();
        }
      } else {
        // Handle non-streaming response (fallback)
        const bytes = await response.response.transformToByteArray();
        completion = new TextDecoder().decode(bytes);
        console.log("Agent Response Text (Non-streaming):", completion);

        // For non-streaming, add the complete response
        setAnswers((prevState) => [
          ...prevState,
          { text: completion, isStreaming: true },
        ]);
        setControlAnswers((prevState) => [
          ...prevState,
          { current_tab_view: "answer" },
        ]);
      }
    } catch (streamError) {
      console.error("Error processing agent response stream:", streamError);
      throw streamError;
    }

    console.log("------- End of Agent Response -------");
    console.log("Complete Streaming Output:", completion);
    return {
      sessionId,
      completion,
      lastKTurns,
    };
  } catch (error) {
    console.error("Error invoking agent core:", error);
    throw error;
  }
};
