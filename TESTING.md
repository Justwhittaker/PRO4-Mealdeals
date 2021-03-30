---
# Mealdeals Testing #
---
## Contents ##
---

* [Testing](#Testing)
    * [Validation Testing](#ValidationTesting)
    * [Unit Testing](#UnitTesting)
    * [Cross Browser/Cross Device Verification](#CrossBrowser)
    * [Accessibility Testing](#AccessibilityTesting)
    * [Automated Testing](#AutomatedTesting)
    * [alignItems](#alignItems)
    * [Members](#Members)
    * [Python Tests](#PythonTests)
    * [Defect Tracking](#DefectTracking)
    * [Noteworthy Bugs](#NoteworthyBugs)
    * [Outstanding Defects](#OutstandingDefects)

---

<a name="Testing"></a>
## Testing ##
---
Jasmine Tests
Travis
---

<a name="ValidationTesting"></a>
### Validation Testing ###
---
* [**CSS Validator**](https://jigsaw.w3.org/css-validator/) - Note, any error associated with root: Imported style sheets are not checked in direct input and file upload modes were ignored.
* [**HTML Validator**](https://jigsaw.w3.org/css-validator/) - validation of HTML with Django is pretty useless as all {{}} bracketed values raise errors. I ran only a few files through the validator and instead relied heavily upon gitpod's IDE to identify mismatched tags and closing Django directives.
* django-extensions - used for validating templates from the command line python manage.py validate_templates
* JavaScript Validator Note any errors for let, variables set in other .js files, and constants were ignored. I also used a more ES6 friendly checker and there were no errors for main.js
* GitPod IDE - Gitpod has inline validation for many file types. Python, CSS, HTML, DJANGO files were continuously tested for validity when using this IDE.


---

<a name="UnitTesting"></a>
### Unit Testing ###
---


---

<a name="CrossBrowser"></a>
### Cross Browser/Cross Device Verification ###
---



---

<a name="AccessibilityTesting"></a>
### Accessibility Testing ###
---



---

<a name="AutomatedTesting"></a>
### Automated Testing ###
---


---

<a name="alignItems"></a>
### alignItems ###
---


---

<a name="Members"></a>
### Members ###
---


---

<a name="DefectTracking"></a>
### Defect Tracking ###
---


---

<a name="NoteworthyBugs"></a>
### Noteworthy Bugs ###
---

---

<a name="Outstanding Defects"></a>
### Outstanding Defects ###
---







*I used **pep8online.com** to test my Python code validator with no issues - http://pep8online.com/checkresult
![pep8](static/img/pep8_test.png)
* I tested the python code with **Python Debugger** - https://realpython.com/python-debugging-pdb/
![pdb](static/img/pdb_debugger.png)
* Also used this **Automated Testing** to test my flask applications - https://www.patricksoftwareblog.com/unit-testing-a-flask-application
![test_flask](static/img/test_flask.png)
* I used **Pylint** to lint my code by Linting my python code - http://pylint.pycqa.org/en/latest/
![test_Pylint](static/img/pylint.png)
* I tested the responsiveness of the website by using the [**Google Chrome Developer Tool**](https://developers.google.com/web/tools/chrome-devtools) as well as the plug-in **Unicorn Revealer** to control my overflow and the website [**Am I Responsive**](http://ami.responsivedesign.is/). 
![AmIresponsive](static/img/amIresponsive.png)
* I also tested my website on **different browsers and real devices** : **Iphone 6s, Ipad Pro 12", Ipad Mini, Google Chrome, Safari, Mozilla Firefox and Samsung A70.**
* I used a first **dirty version** of this project on **Gitpod** and **refactored** my code **step by step** to remove any **useless classes**
* I tested my CSS file and my HTML files using [**CSS Validator**](https://jigsaw.w3.org/css-validator/) and [**HTML Validator**](https://validator.w3.org/) then fixed the issues needed to be fixed.
![test_Html](static/img/errors_val_w3.png)
![test_CSS](static/img/errors_val_w3_css.png)
* I tested every **functions** of my script.js using multiple **console.log** and checking for **errors** in the **Google Chrome console**.
* I passed my deployed app through **Lighthouse** with the follwoing results
![lighthouse](static/img/lighthouse.png)
* All pages passed the HTML,CSS and Python validator final test with no major issues.
