// custom javascript
(function() {
  console.log('Sanity Check!');
})();

function handleClickTest() {
  let topic = document.getElementById("topic").value;
  alert(topic)
}

function handleTopicSearch() {
  const sr = document.getElementById("searchResult");

  const spinner = `<span>Loading...</span>`
  sr.innerHTML = spinner;

  let topic = document.getElementById("topicSearch").value;

  fetch(`/topic/${topic}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
  })
  .then(response => response.json())
  .then(res => {
    const topic = res.topic;
    const pages = res.pages;
    const results = res.results;

    const html = `
      <div>
        <span>topic: ${topic} / </span>
        <span>pages: ${pages} / </span>
        <span>results: ${results}</span>
      </div>`;

    sr.innerHTML = html;

  })
  .catch(err => console.log(err));
}

function handleClick() {
  let tables= document.getElementById("tasks");
  tables.innerHTML = ""

  let topic = document.getElementById("topic").value;
  fetch('/tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ topic: topic }),
  })
  .then(response => response.json())
  .then(data => getStatus(data.task_id));
}

function getStatus(taskID) {
  fetch(`/tasks/${taskID}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
  })
  .then(response => response.json())
  .then(res => {
    const taskStatus = res.task_status;
    let taskResult = res.task_result
    if (taskStatus === 'SUCCESS') {
      taskResult = "<a href='./reports/github_topic_contributors_gig.csv' target='_blank'>" + res.task_result + "</a>";
    }

    const html = `
      <tr>
        <td>${taskID}</td>
        <td>${taskStatus}</td>
        <td>${taskResult}</td>
      </tr>`;
    const newRow = document.getElementById('tasks').insertRow(0);
    newRow.innerHTML = html;

    if (taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') return false;
    setTimeout(function() {
      getStatus(res.task_id);
    }, 3000);
  })
  .catch(err => console.log(err));
}
