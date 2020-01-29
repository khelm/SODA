//////////////////////// Prepare metadata //////////////////////////////
function showAwardInfo(){
    document.getElementById('div-add-award').style.display ='block';
    document.getElementById('div-add-contributor').style.display ='none';
    document.getElementById('div-add-milestone').style.display ='none';
}
function showContributorInfo() {
  document.getElementById('div-add-contributor').style.display ='block';
  document.getElementById('div-add-award').style.display ='none';
  document.getElementById('div-add-milestone').style.display ='none';
}
function showMilestoneInfo() {
  document.getElementById('div-add-milestone').style.display ='block';
  document.getElementById('div-add-award').style.display ='none';
  document.getElementById('div-add-contributor').style.display ='none';
}
function showExistingAwards() {
  document.getElementById('div-existing-award').style.display ='block';
  document.getElementById('div-new-award').style.display ='none';
}
function showNewAwards() {
  document.getElementById('div-new-award').style.display ='block';
  document.getElementById('div-existing-award').style.display ='none';
}
function showExistingMilestones() {
  document.getElementById('div-existing-milestone').style.display ='block';
  document.getElementById('div-new-milestone').style.display ='none';
}
function showNewMilestones() {
  document.getElementById('div-new-milestone').style.display ='block';
  document.getElementById('div-existing-milestone').style.display ='none';
}

document.querySelector('#input-add-award').addEventListener('click', () => {
    showAwardInfo();
    table_award.redraw()
})
document.querySelector('#input-add-contributor').addEventListener('click', () => {
    showContributorInfo();
    table_con.redraw()
})
document.querySelector('#input-add-milestone').addEventListener('click', () => {
    showMilestoneInfo();
    table_milestone.redraw()
})
// Prepare Submission File
document.querySelector('#input-choose-existing-award').addEventListener('click', () => {
    showExistingAwards();
})
document.querySelector('#input-new-award').addEventListener('click', () => {
    showNewAwards();
})
document.querySelector('#input-choose-existing-milestone').addEventListener('click', () => {
    showExistingMilestones();
})
document.querySelector('#input-new-milestone').addEventListener('click', () => {
    showNewMilestones();
})


///////////////////////////////Curate/////////////////////////////////////
function showModifyExisting(){
  document.getElementById('div-create-new').style.display ='none';
  document.getElementById('div-create-cloud').style.display ='none';
  document.getElementById('div-curate-button').style.display ='block';
  document.getElementById('div-curate-progress-bar-error-status').style.display ='block';
  document.getElementById('div-curate-progress-bar-status').style.display ='block';
  // document.getElementById('div-progress-print').style.display ='none';
  // document.getElementById('progressinfo').value ='';
  document.getElementById("para-curate-progress-bar-error-status").innerHTML = ""
  document.getElementById("para-curate-progress-bar-status").innerHTML = ""
  document.getElementById("div-curate-meter-progress").style.display ='none';
  document.getElementById("progress-bar-curate").value = 0;
}

function showCreateNew(){
  document.getElementById('div-create-new').style.display ='block';
  document.getElementById('div-create-cloud').style.display ='none';
  document.getElementById('div-curate-button').style.display ='block';
  document.getElementById('div-curate-progress-bar-error-status').style.display ='block';
  document.getElementById('div-curate-progress-bar-status').style.display ='block';
  // document.getElementById('div-progress-print').style.display ='none';
  // document.getElementById('progressinfo').value ='';
  document.getElementById("para-curate-progress-bar-error-status").innerHTML = ""
  document.getElementById("para-curate-progress-bar-status").innerHTML = ""
  document.getElementById("div-curate-meter-progress").style.display ='block';
  document.getElementById("progress-bar-curate").value = 0;
}

function showCreateCloud(){
  document.getElementById('div-create-new').style.display ='none';
  document.getElementById('div-create-cloud').style.display ='block';
  document.getElementById('div-curate-button').style.display ='block';
  document.getElementById('div-curate-progress-bar-error-status').style.display ='block';
  document.getElementById('div-curate-progress-bar-status').style.display ='block';
  // document.getElementById('div-progress-print').style.display ='none';
  document.getElementById("para-curate-progress-bar-error-status").innerHTML = ""
  document.getElementById("para-curate-progress-bar-status").innerHTML = ""
  document.getElementById("div-curate-meter-progress").style.display ='block';
  document.getElementById("progress-bar-curate").value = 0;
}

document.querySelector('#existing-dataset').addEventListener('click', () => {
    showModifyExisting()
})
document.querySelector('#create-newdataset').addEventListener('click', () => {
    showCreateNew()
})
document.querySelector('#cloud-dataset').addEventListener('click', () => {
    showCreateCloud()
})


function showSelectSubmission(){
  document.getElementById('div-existing-submission').style.display ='block';
}

function showNewSubmission(){
  document.getElementById('div-existing-submission').style.display ='none';
}

function showNoSubmission(){
  document.getElementById('div-existing-submission').style.display ='none';
}

document.querySelector('#existing-submission').addEventListener('click', () => {
    showSelectSubmission()
})
document.querySelector('#new-submission').addEventListener('click', () => {
    showNewSubmission()
})
document.querySelector('#no-submission').addEventListener('click', () => {
    showNoSubmission()
})


function showSelectDescription(){
  document.getElementById('div-existing-description').style.display ='block';
}

function showNewDescription(){
  document.getElementById('div-existing-description').style.display ='none';
}

function showNoDescription(){
  document.getElementById('div-existing-description').style.display ='none';
}

document.querySelector('#existing-description').addEventListener('click', () => {
    showSelectDescription()
})
document.querySelector('#new-description').addEventListener('click', () => {
    showNewDescription()
})
document.querySelector('#no-description').addEventListener('click', () => {
    showNoDescription()
})


function showSelectSubjects(){
  document.getElementById('div-existing-subjects').style.display ='block';
}

function showNewSubjects(){
  document.getElementById('div-existing-subjects').style.display ='none';
}

function showNoSubjects(){
  document.getElementById('div-existing-subjects').style.display ='none';
}

document.querySelector('#existing-subjects').addEventListener('click', () => {
    showSelectSubjects()
})
document.querySelector('#new-subjects').addEventListener('click', () => {
    showNewSubjects()
})
document.querySelector('#no-subjects').addEventListener('click', () => {
    showNoSubjects()
})


function showSelectSamples(){
  document.getElementById('div-existing-samples').style.display ='block';
}

function showNewSamples(){
  document.getElementById('div-existing-samples').style.display ='none';
}

function showNoSamples(){
  document.getElementById('div-existing-samples').style.display ='none';
}

document.querySelector('#existing-samples').addEventListener('click', () => {
    showSelectSamples()
})
document.querySelector('#new-samples').addEventListener('click', () => {
    showNewSamples()
})
document.querySelector('#no-samples').addEventListener('click', () => {
    showNoSamples()
})

function showPreorganizedDataset(){
  document.getElementById('div-pre-organized-dataset').style.display ='block';
  document.getElementById('div-organize-dataset').style.display ='none';
  document.getElementById('div-smart-organize-dataset').style.display ='none';
  document.getElementById('para-save-file-organization-status').innerHTML = '';
  document.getElementById('div-save-table').style.display ='block';
  document.getElementById('div-smart-organize').style.display ='none';
  document.getElementById('div-clear-table').style.display ='block';
  document.getElementById('div-existing-dataset').style.display ='block';
}

function showOrganizeDataset(){
  document.getElementById('div-pre-organized-dataset').style.display ='none';
  document.getElementById('div-organize-dataset').style.display ='block';
  document.getElementById('div-smart-organize-dataset').style.display ='none';
  document.getElementById('para-save-file-organization-status').innerHTML = '';
  document.getElementById('div-save-table').style.display ='block';
  document.getElementById('div-smart-organize').style.display ='block';
  document.getElementById('div-clear-table').style.display ='block';
  document.getElementById('div-existing-dataset').style.display ='none';
}


document.querySelector('#preorganized-dataset').addEventListener('click', () => {
    showPreorganizedDataset()
})
document.querySelector('#organize-dataset').addEventListener('click', () => {
    showOrganizeDataset()
})
