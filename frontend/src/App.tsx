import React, { useState } from "react";
import {
  TextField,
  Typography,
  Box,
  CircularProgress,
  Button,
  Tabs,
  Tab,
} from "@mui/material";
import { useSnackbar } from "notistack";
import ReactMarkdown from "react-markdown";

const App = () => {
  const [repoUrls, setRepoUrls] = useState<string>("");
  const [readmes, setReadmes] = useState<{ [repoUrl: string]: string }>({});
  const [followUpPrompts, setFollowUpPrompts] = useState<{
    [repoUrl: string]: string;
  }>({});
  const { enqueueSnackbar } = useSnackbar();
  const [sockets, setSockets] = useState<{ [repoUrl: string]: WebSocket | null }>(
    {}
  );
  const [isLoading, setIsLoading] = useState<{ [repoUrl: string]: boolean }>({});
  const [activeTab, setActiveTab] = useState(0);

  const handleRepoUrlsChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setRepoUrls(event.target.value);
  };

  const handleFollowUpPromptChange = (
    event: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>,
    repoUrl: string
  ) => {
    setFollowUpPrompts((prevPrompts) => ({
      ...prevPrompts,
      [repoUrl]: event.target.value,
    }));
  };

  const handleSubmit = async (repoUrl: string) => {
    if (!repoUrl) {
      enqueueSnackbar("Please enter a valid repo URL", { variant: "error" });
      return;
    }

    const newSocket = new WebSocket(
      "wss://8000-workstation-lp10lyw7.cluster-5bedb2o55nhusvppd7wbvrifho.cloudworkstations.dev/ws"
    );

    newSocket.onopen = () => {
      console.log("WebSocket connection established for", repoUrl);
      setSockets((prevSockets) => ({ ...prevSockets, [repoUrl]: newSocket }));
      setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: true }));
      newSocket.send(
        JSON.stringify({ action: "analyze", repoUrl: repoUrl })
      );
      enqueueSnackbar(`Analyzing repository: ${repoUrl}`, {
        variant: "info",
      });
    };

    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        enqueueSnackbar(data.error, { variant: "error" });
        setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: false }));
      } else if (data.readme) {
        setReadmes((prevReadmes) => ({
          ...prevReadmes,
          [repoUrl]: data.readme,
        }));
        setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: false }));
      } else if (data.response) {
        setReadmes((prevReadmes) => ({
          ...prevReadmes,
          [repoUrl]: data.response,
        }));
        setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: false }));
      }
    };

    newSocket.onerror = (error) => {
      console.error("WebSocket error for", repoUrl, ":", error);
      enqueueSnackbar(`WebSocket error for ${repoUrl}`, {
        variant: "error",
      });
      setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: false }));
    };
  };

  const handleSendFollowUp = async (repoUrl: string) => {
    const prompt = followUpPrompts[repoUrl];
    if (!prompt) {
      enqueueSnackbar("Please enter a follow-up prompt", { variant: "error" });
      return;
    }

    const socket = sockets[repoUrl];
    if (socket) {
      setIsLoading((prevLoading) => ({ ...prevLoading, [repoUrl]: true }));
      socket.send(
        JSON.stringify({ action: "prompt", message: prompt })
      );
      setFollowUpPrompts((prevPrompts) => ({ ...prevPrompts, [repoUrl]: "" }));
      enqueueSnackbar(`Sending follow-up prompt for ${repoUrl}...`, {
        variant: "info",
      });
    } else {
      enqueueSnackbar(`Error: WebSocket connection not established for ${repoUrl}`, {
        variant: "error",
      });
    }
  };

  const downloadTxtFile = (repoUrl: string) => {
    const element = document.createElement("a");
    const file = new Blob([readmes[repoUrl]], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `${repoUrl.replace(/[^a-zA-Z0-9]/g, "_")}.md`;
    document.body.appendChild(element);
    element.click();
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <div className="flex flex-col px-8 min-w-fit mt-12">
      <div className="flex flex-col gap-6 items-start pb-12">
        <div>
          <Typography variant="h4" component="h1" gutterBottom>
            README Generator
          </Typography>
          <Typography variant="body1" className="pb-8">
            Enter one Github/Gitlab repository URL per line to generate
            READMEs.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Repo URLs"
            value={repoUrls}
            onChange={handleRepoUrlsChange}
          />
          <Button
            onClick={() => {
              repoUrls?.split("\n").forEach((repoUrl) => handleSubmit(repoUrl.trim()));
            }}
          >
            Generate Readmes
          </Button>
        </div>
        <div className="min-w-max">
          <Typography variant="h5" component="h2" gutterBottom>
            Follow-up Prompt
          </Typography>
          <Tabs value={activeTab} onChange={handleTabChange} className="mb-4">
            {repoUrls.split("\n").filter(url => url.trim()).map((repoUrl) => (
              <Tab key={repoUrl} label={repoUrl.split("/")[repoUrl.split("/").length-1]} />
            ))}
          </Tabs>
          {repoUrls.split("\n").filter(url => url.trim()).map((repoUrl, index) => (
            <div
              key={repoUrl}
              hidden={activeTab !== index}
              className="min-w-max"
            >
              <Typography variant="body1" className="pb-8">
                Refine the generated Readme for {repoUrl}
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                value={followUpPrompts[repoUrl] || ""}
                onChange={(event) =>
                  handleFollowUpPromptChange(event, repoUrl)
                }
              />
              <Button onClick={() => handleSendFollowUp(repoUrl)}>
                Send Follow-up
              </Button>
            </div>
          ))}
        </div>
      </div>
      <Typography variant="h5" component="h2" gutterBottom>
        Generated Readme
      </Typography>

      <div className="prose min-w-[90vh]">
        <Tabs value={activeTab} onChange={handleTabChange} className="mb-4">
          {repoUrls.split("\n").filter(url => url.trim()).map((repoUrl) => (
            <Tab key={repoUrl} label={repoUrl.split("/")[repoUrl.split("/").length-1]} />
          ))}
        </Tabs>
        {repoUrls.split("\n").filter(url => url.trim()).map((repoUrl, index) => (
          <div key={repoUrl} hidden={activeTab !== index}>
            {isLoading[repoUrl] && <CircularProgress />}
            {readmes[repoUrl] && !isLoading[repoUrl] && (
              <>
                <Button
                  variant="contained"
                  onClick={() => downloadTxtFile(repoUrl)}
                >
                  Download README.md
                </Button>
                <ReactMarkdown>{readmes[repoUrl]}</ReactMarkdown>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
