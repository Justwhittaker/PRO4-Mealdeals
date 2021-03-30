---
# Mealdeals Testing #
---
## Contents ##
---

* [Testing](#Testing)
    * [Validation Testing](#ValidationTesting)
    * [Unit Testing](#UnitTesting)
    * [Cross Browser/Cross Device Verification](#CrossBrowser)
    * [Python Tests](#PythonTests)
    * [Troubleshooting](#Troubleshooting)
    * [Outstanding Defects](#OutstandingDefects)

---

<a name="Testing"></a>
## Testing ##
---

---

<a name="ValidationTesting"></a>
### Validation Testing ###
---
* [**CSS Validator**](https://jigsaw.w3.org/css-validator/) - Note, any error associated with root: Imported style sheets are not checked in direct input and file upload modes were ignored.
* [**HTML Validator**](https://jigsaw.w3.org/css-validator/) - validation of HTML with Django is pretty useless as all {{}} bracketed values raise errors. I ran only a few files through the validator and instead relied heavily upon gitpod's IDE to identify mismatched tags and closing Django directives.
* [**django-extensions**](https://pypi.org/project/django-extensions/) - used for validating templates from the command line python manage.py validate_templates
* [**JavaScript Validator**](https://beautifytools.com/javascript-validator.php) Note any errors for let, variables set in other .js files, and constants were ignored. 
* [**GitPod IDE**](https://gitpod.io/) - Gitpod has inline validation for many file types. Python, CSS, HTML, DJANGO files were continuously tested for validity when using this IDE.


---

<a name="UnitTesting"></a>
### Unit Testing ###
---

As core functionality and features were delivered I attempted to create python tests to ensure functionality was not lost. I got behind after a point, but made up ground at the end to get some coverage of all models, forms and views.

---

<a name="CrossBrowser"></a>
### Cross Browser/Cross Device Verification ###
---

To verify that the application is functional and looks pleasant across various operating systems and device sizes
These tests are light on the functionality with more attention being paid to the layout and console logs:

Operating systems and screen sizes is as follows:

INSERT THE TEST results



---

<a name="PythonTests"></a>
### Python Tests ###
---

Tests were written for Django views, forms, models. These files are located in each application specific /test folders and named in the following manner:

* test_forms.py - for tests concerning forms
* test_models.py - for tests concerning models
* test_views.py - for tests concerning views

COVERAGE REPORTS
---

<a name="Troubleshooting"></a>
## Troubleshooting ##
---

As I had a few learning curves by using Django frameworks there were a lot of errors I needed to work through and understand, I wanted to document a lot of my learning opportunities through this project. See the separate [ERRORS.md](ERRORS.md) file for the details.

---

<a name="Outstanding Defects"></a>
### Outstanding Defects ###
---

Takes a while to get to the next page when uploading files - I should add in a file processing status bar so user's know what is going on. The static state of the selected submit button is some visual indicator but I should prevent user input during this wait.

Inefficient Email - I should use a celery task or distributed system to handle emailing users. Right now it's all inline and not done asynchronously thus adding to the time it takes to create a contact form.

No system timeout - User's login seems to last forever, should auto log users out after half an hour to keep accounts secure
